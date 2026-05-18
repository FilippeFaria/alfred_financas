import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/env/app_env.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/sms_capture_preferences_dto.dart';

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  static const MethodChannel _notificationChannel =
      MethodChannel('alfred_financas/notifications');

  bool _loadingSms = true;
  bool _savingSms = false;
  bool _importandoSmsRetroativos = false;
  bool _smsEnabled = false;
  bool _smsReceivePermissionGranted = false;
  bool _smsReadPermissionGranted = false;
  List<SmsBankCatalogItemDto> _catalogoBancos = const [];
  List<String> _catalogoCartoes = const [];
  final Set<String> _bancosSelecionados = <String>{};
  final Map<String, TextEditingController> _controladoresCartao =
      <String, TextEditingController>{};

  @override
  void initState() {
    super.initState();
    _carregarPreferenciasSms();
    _sincronizarPermissaoSms();
  }

  @override
  void dispose() {
    for (final controller in _controladoresCartao.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _carregarPreferenciasSms() async {
    setState(() {
      _loadingSms = true;
    });
    try {
      final client = ref.read(alfredApiClientProvider);
      final prefs = await client.getSmsCapturePreferences();
      if (!mounted) return;
      setState(() {
        _smsEnabled = prefs.smsEnabled;
        _catalogoBancos = prefs.catalogoBancos;
        _catalogoCartoes = prefs.catalogoCartoes;
        _bancosSelecionados
          ..clear()
          ..addAll(prefs.bancosSelecionados);
      });
      _sincronizarControladoresCartao(prefs.mapeamentoCartaoUltimos4);
      await _sincronizarConfigNativa();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Nao foi possivel carregar preferencias de SMS.')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loadingSms = false;
        });
      }
    }
  }

  void _sincronizarControladoresCartao(Map<String, String> mapping) {
    final alvo = <String>{..._catalogoCartoes};
    for (final cartao in alvo) {
      final existente = _controladoresCartao[cartao];
      if (existente == null) {
        _controladoresCartao[cartao] =
            TextEditingController(text: mapping[cartao] ?? '');
      } else {
        existente.text = mapping[cartao] ?? '';
      }
    }
    final paraRemover =
        _controladoresCartao.keys.where((key) => !alvo.contains(key)).toList();
    for (final key in paraRemover) {
      _controladoresCartao.remove(key)?.dispose();
    }
  }

  Future<void> _sincronizarPermissaoSms() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      setState(() {
        _smsReceivePermissionGranted = false;
        _smsReadPermissionGranted = false;
      });
      return;
    }
    try {
      final raw = await _notificationChannel
          .invokeMethod<Map<dynamic, dynamic>>('getSmsPermissionStatus');
      final status = Map<String, dynamic>.from(raw ?? const {});
      if (!mounted) return;
      setState(() {
        _smsReceivePermissionGranted = status['receive_sms'] == true;
        _smsReadPermissionGranted = status['read_sms'] == true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _smsReceivePermissionGranted = false;
        _smsReadPermissionGranted = false;
      });
    }
  }

  Future<void> _pedirPermissaoSms() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await _notificationChannel.invokeMethod<bool>('requestSmsPermission');
      await _sincronizarPermissaoSms();
      if (!mounted) return;
      final granted =
          _smsReceivePermissionGranted && _smsReadPermissionGranted;
      if (!granted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Permissao de SMS incompleta. Verifique RECEIVE_SMS e READ_SMS.',
            ),
          ),
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Nao foi possivel solicitar permissao de SMS.')),
      );
    }
  }

  Future<void> _importarSmsRetroativos({required int horas}) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    if (_importandoSmsRetroativos) return;

    setState(() {
      _importandoSmsRetroativos = true;
    });
    try {
      await _notificationChannel.invokeMethod<bool>('requestSmsPermission');
      await _sincronizarPermissaoSms();
      if (!mounted) return;
      final granted =
          _smsReceivePermissionGranted && _smsReadPermissionGranted;
      if (!granted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Permissao SMS incompleta para importar historico (faltou READ_SMS ou RECEIVE_SMS).',
            ),
          ),
        );
        return;
      }

      final importResultRaw =
          await _notificationChannel.invokeMethod<Map<dynamic, dynamic>>(
        'importRecentSmsEvents',
        {
          'hours': horas,
          'max_items': 250,
        },
      );
      final importResult =
          Map<String, dynamic>.from(importResultRaw ?? const {});
      final imported = (importResult['imported'] as num?)?.toInt() ?? 0;
      final scanned = (importResult['scanned'] as num?)?.toInt() ?? 0;
      final blocked = importResult['blocked'] == true;

      if (!mounted) return;
      if (blocked) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content:
                  Text('Permissao SMS incompleta para importar historico.')),
        );
        return;
      }

      final client = ref.read(alfredApiClientProvider);
      final pendingRaw = await _notificationChannel
          .invokeMethod<List<dynamic>>('listPendingSmsEvents');
      final pending = (pendingRaw ?? const <dynamic>[])
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();

      var created = 0;
      var duplicate = 0;
      var ignored = 0;
      var failed = 0;
      for (final sms in pending) {
        final sender = (sms['sender'] ?? '').toString().trim();
        final text = (sms['text'] ?? '').toString().trim();
        final receivedAt = (sms['received_at'] ?? '').toString().trim();
        final smsMessageId = (sms['sms_message_id'] ?? '').toString().trim();
        if (sender.isEmpty ||
            text.isEmpty ||
            receivedAt.isEmpty ||
            smsMessageId.isEmpty) {
          continue;
        }
        try {
          final response = await client.postAiSmsTransacao(
            sender: sender,
            text: text,
            receivedAt: receivedAt,
            smsMessageId: smsMessageId,
          );
          await _notificationChannel.invokeMethod<void>(
            'removePendingSmsEvent',
            {'sms_message_id': smsMessageId},
          );
          if (response.created) {
            created += 1;
          } else if (response.duplicate) {
            duplicate += 1;
          } else {
            ignored += 1;
          }
        } catch (_) {
          failed += 1;
        }
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Importacao ${horas}h: lidos $scanned, enfileirados $imported, '
            'pendencias criadas $created, duplicados $duplicate, ignorados $ignored, falhas $failed.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Nao foi possivel importar SMS retroativos.')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _importandoSmsRetroativos = false;
        });
      }
    }
  }

  Map<String, String> _coletarMapeamento() {
    final resultado = <String, String>{};
    for (final entry in _controladoresCartao.entries) {
      final valor = entry.value.text.trim();
      if (valor.isEmpty) continue;
      resultado[entry.key] = valor;
    }
    return resultado;
  }

  bool _validarMapeamentoLocal(Map<String, String> mapping) {
    final sufixos = <String>{};
    for (final entry in mapping.entries) {
      final valor = entry.value.trim();
      if (!RegExp(r'^\d{4}$').hasMatch(valor)) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Digite 4 digitos validos para "${entry.key}".')),
        );
        return false;
      }
      if (sufixos.contains(valor)) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('O sufixo $valor nao pode ser repetido.')),
        );
        return false;
      }
      sufixos.add(valor);
    }
    return true;
  }

  Future<void> _salvarPreferenciasSms() async {
    final mapping = _coletarMapeamento();
    if (!_validarMapeamentoLocal(mapping)) return;

    setState(() {
      _savingSms = true;
    });
    try {
      final client = ref.read(alfredApiClientProvider);
      final atualizado = await client.putSmsCapturePreferences(
        SmsCapturePreferencesUpdateDto(
          smsEnabled: _smsEnabled,
          bancosSelecionados: _bancosSelecionados.toList()..sort(),
          mapeamentoCartaoUltimos4: mapping,
        ),
      );
      if (!mounted) return;
      setState(() {
        _smsEnabled = atualizado.smsEnabled;
        _catalogoBancos = atualizado.catalogoBancos;
        _catalogoCartoes = atualizado.catalogoCartoes;
        _bancosSelecionados
          ..clear()
          ..addAll(atualizado.bancosSelecionados);
      });
      _sincronizarControladoresCartao(atualizado.mapeamentoCartaoUltimos4);
      await _sincronizarConfigNativa();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Preferencias de SMS salvas com sucesso.')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Nao foi possivel salvar preferencias de SMS.')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _savingSms = false;
        });
      }
    }
  }

  Future<void> _sincronizarConfigNativa() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await _notificationChannel.invokeMethod(
        'setSmsCaptureConfig',
        {
          'sms_enabled': _smsEnabled,
          'bancos_selecionados': _bancosSelecionados.toList()..sort(),
          'mapeamento_cartao_ultimos4': _coletarMapeamento(),
        },
      );
    } catch (_) {
      // Melhor esforco: nao bloqueia a tela.
    }
  }

  @override
  Widget build(BuildContext context) {
    final flavor = AppEnv.flavor.name;
    final baseUrl = AppEnv.apiBaseUrl;
    final suportaSmsAndroid =
        !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
    final smsPermissionGranted =
        _smsReceivePermissionGranted && _smsReadPermissionGranted;

    return Scaffold(
      appBar: AppBar(title: const Text('Ajustes')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.flag_outlined),
              title: const Text('Ambiente'),
              subtitle: Text(flavor.toUpperCase()),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.link_outlined),
              title: const Text('API Base URL'),
              subtitle: Text(baseUrl),
              trailing: IconButton(
                tooltip: 'Copiar URL',
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: baseUrl));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                          content: Text(
                              'URL copiada para a area de transferencia.')),
                    );
                  }
                },
                icon: const Icon(Icons.copy),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _loadingSms
                  ? const Center(child: CircularProgressIndicator())
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Captura por SMS',
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 12),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title:
                              const Text('Ativar captura automatica por SMS'),
                          value: _smsEnabled,
                          onChanged: (value) {
                            setState(() {
                              _smsEnabled = value;
                            });
                          },
                        ),
                        if (suportaSmsAndroid) ...[
                          const SizedBox(height: 6),
                          Text(
                            'Captura em tempo real (RECEIVE_SMS): ${_smsReceivePermissionGranted ? "ativa" : "inativa"}',
                          ),
                          Text(
                            'RECEIVE_SMS: ${_smsReceivePermissionGranted ? "concedida" : "nao concedida"}',
                          ),
                          Text(
                            'READ_SMS: ${_smsReadPermissionGranted ? "concedida" : "nao concedida"}',
                          ),
                          Text(
                            'Importacao de historico: ${smsPermissionGranted ? "disponivel" : "indisponivel"}',
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              OutlinedButton.icon(
                                onPressed: _pedirPermissaoSms,
                                icon: const Icon(Icons.sms_outlined),
                                label: const Text('Conceder permissao SMS'),
                              ),
                              OutlinedButton.icon(
                                onPressed: _sincronizarPermissaoSms,
                                icon: const Icon(Icons.refresh_outlined),
                                label: const Text('Atualizar status'),
                              ),
                              OutlinedButton.icon(
                                onPressed: _importandoSmsRetroativos
                                    ? null
                                    : () => _importarSmsRetroativos(horas: 24),
                                icon: _importandoSmsRetroativos
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2),
                                      )
                                    : const Icon(Icons.history_outlined),
                                label: const Text('Importar ultimas 24h'),
                              ),
                              OutlinedButton.icon(
                                onPressed: _importandoSmsRetroativos
                                    ? null
                                    : () => _importarSmsRetroativos(horas: 48),
                                icon: const Icon(Icons.schedule_outlined),
                                label: const Text('Importar ultimas 48h'),
                              ),
                            ],
                          ),
                        ] else ...[
                          const Text(
                            'A captura de SMS fica disponivel apenas no Android.',
                            style: TextStyle(color: Colors.black54),
                          ),
                        ],
                        const SizedBox(height: 14),
                        const Text('Bancos monitorados'),
                        const SizedBox(height: 8),
                        if (_catalogoBancos.isEmpty)
                          const Text('Nenhum banco disponivel.',
                              style: TextStyle(color: Colors.black54))
                        else
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: _catalogoBancos
                                .map(
                                  (banco) => FilterChip(
                                    label: Text(banco.nome),
                                    selected:
                                        _bancosSelecionados.contains(banco.id),
                                    onSelected: (selected) {
                                      setState(() {
                                        if (selected) {
                                          _bancosSelecionados.add(banco.id);
                                        } else {
                                          _bancosSelecionados.remove(banco.id);
                                        }
                                      });
                                    },
                                  ),
                                )
                                .toList(),
                          ),
                        const SizedBox(height: 14),
                        const Text('Mapeamento de cartoes (ultimos 4 digitos)'),
                        const SizedBox(height: 8),
                        if (_catalogoCartoes.isEmpty)
                          const Text('Nenhum cartao disponivel.',
                              style: TextStyle(color: Colors.black54))
                        else
                          ..._catalogoCartoes.map((cartao) {
                            final controller = _controladoresCartao[cartao] ??
                                TextEditingController();
                            _controladoresCartao.putIfAbsent(
                                cartao, () => controller);
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: TextField(
                                controller: controller,
                                maxLength: 4,
                                keyboardType: TextInputType.number,
                                decoration: InputDecoration(
                                  labelText: cartao,
                                  hintText: '1234',
                                  border: const OutlineInputBorder(),
                                  counterText: '',
                                ),
                              ),
                            );
                          }),
                        const SizedBox(height: 8),
                        FilledButton.icon(
                          onPressed: _savingSms ? null : _salvarPreferenciasSms,
                          icon: _savingSms
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.save_outlined),
                          label: const Text('Salvar preferencias de SMS'),
                        ),
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Sobre este app',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'O mobile foi pensado para leitura rapida, com foco em dashboard, lancamentos '
                    'e insights. A proxima evolucao deve conectar preferencias, autenticacao e '
                    'sincronizacao mais fina com o backend.',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
