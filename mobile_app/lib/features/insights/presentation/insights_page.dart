import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:record/record.dart';

import '../../../core/notifications/local_notification_service.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/dto/ai_transacao_dto.dart';
import '../../../core/network/dto/pending_transaction_dto.dart';
import '../../../core/utils/formatters.dart';
import '../data/insights_repository.dart';

class InsightsPage extends ConsumerStatefulWidget {
  const InsightsPage({super.key});

  @override
  ConsumerState<InsightsPage> createState() => _InsightsPageState();
}

class _InsightsPageState extends ConsumerState<InsightsPage> with WidgetsBindingObserver {
  static const MethodChannel _notificationChannel = MethodChannel('alfred_financas/notifications');

  final TextEditingController _textoController = TextEditingController();
  final AudioRecorder _audioRecorder = AudioRecorder();

  bool _interpretando = false;
  bool _confirmando = false;
  bool _ignorando = false;
  bool _gravandoAudio = false;
  bool _interpretandoAudio = false;
  bool _notificationPermissionActive = false;
  bool _loadingNotificationStatus = false;
  String? _lastNotificationProcessedAt;
  bool _processingNotifications = false;
  bool _loadingPendenciasNotificacao = false;
  List<PendingTransactionDto> _pendenciasNotificacao = const [];

  String? _audioFilePath;
  List<int>? _audioBytes;
  String? _audioFileName;
  StreamSubscription<Uint8List>? _audioStreamSubscription;
  final List<int> _audioPcmBuffer = [];
  String? _transcricaoAudio;
  TextoParaTransacaoResponseDto? _resultado;
  final Set<String> _processedNotificationKeys = <String>{};

  double? _extrairValorDaNotificacao(String text) {
    final regex = RegExp(r'r\$\s*([0-9\.\,]+)', caseSensitive: false);
    final match = regex.firstMatch(text);
    if (match == null) return null;
    final raw = (match.group(1) ?? '').replaceAll('.', '').replaceAll(',', '.').trim();
    return double.tryParse(raw);
  }

  String _extrairNomeDaNotificacao(String text) {
    final em = RegExp(r'\bem\s+(.+)$', caseSensitive: false).firstMatch(text);
    final para = RegExp(r'\bpara\s+(.+?)(?:,|\.)', caseSensitive: false).firstMatch(text);
    final nome = (em?.group(1) ?? para?.group(1) ?? '').trim();
    if (nome.isEmpty) return 'Transacao detectada';
    return nome.split(',').first.trim();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _sincronizarStatusNotificacoes(processQueue: true);
    _carregarPendenciasNotificacao();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _textoController.dispose();
    _audioStreamSubscription?.cancel();
    _audioRecorder.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _sincronizarStatusNotificacoes(processQueue: true);
    }
  }

  List<int> _pcm16MonoToWav({
    required List<int> pcmBytes,
    int sampleRate = 16000,
    int numChannels = 1,
    int bitsPerSample = 16,
  }) {
    final byteRate = sampleRate * numChannels * bitsPerSample ~/ 8;
    final blockAlign = numChannels * bitsPerSample ~/ 8;
    final dataLength = pcmBytes.length;
    final totalLength = 44 + dataLength;

    final bytes = ByteData(44);
    bytes.setUint32(0, 0x52494646, Endian.big); // RIFF
    bytes.setUint32(4, totalLength - 8, Endian.little);
    bytes.setUint32(8, 0x57415645, Endian.big); // WAVE
    bytes.setUint32(12, 0x666d7420, Endian.big); // fmt
    bytes.setUint32(16, 16, Endian.little); // PCM header size
    bytes.setUint16(20, 1, Endian.little); // PCM
    bytes.setUint16(22, numChannels, Endian.little);
    bytes.setUint32(24, sampleRate, Endian.little);
    bytes.setUint32(28, byteRate, Endian.little);
    bytes.setUint16(32, blockAlign, Endian.little);
    bytes.setUint16(34, bitsPerSample, Endian.little);
    bytes.setUint32(36, 0x64617461, Endian.big); // data
    bytes.setUint32(40, dataLength, Endian.little);

    return <int>[...bytes.buffer.asUint8List(), ...pcmBytes];
  }

  String _formatarData(String? valor) {
    if (valor == null || valor.trim().isEmpty) return '-';
    final raw = valor.trim();
    try {
      if (raw.contains('T')) {
        final dt = DateTime.parse(raw);
        return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
      }
      final data = DateTime.parse('${raw}T00:00:00');
      return '${data.day.toString().padLeft(2, '0')}/${data.month.toString().padLeft(2, '0')}/${data.year}';
    } catch (_) {
      return raw;
    }
  }

  String _labelConfianca(double confianca) {
    if (confianca >= 0.85) return 'Alta';
    if (confianca >= 0.6) return 'Media';
    return 'Baixa';
  }

  String _mensagemErro(Object error) {
    if (error is ApiException) return error.message;
    return 'Nao foi possivel concluir a operacao. Tente novamente.';
  }

  String _formatarUltimoProcessamento(String? value) {
    if (value == null || value.trim().isEmpty) return '-';
    try {
      final parsed = DateTime.parse(value).toLocal();
      final agora = DateTime.now();
      final isHoje = parsed.year == agora.year && parsed.month == agora.month && parsed.day == agora.day;
      final hh = parsed.hour.toString().padLeft(2, '0');
      final mm = parsed.minute.toString().padLeft(2, '0');
      if (isHoje) return 'hoje as $hh:$mm';
      return '${parsed.day.toString().padLeft(2, '0')}/${parsed.month.toString().padLeft(2, '0')} as $hh:$mm';
    } catch (_) {
      return value;
    }
  }

  String _formatarDataHoraDeteccao(DateTime? dataHora) {
    if (dataHora == null) return '-';
    final local = dataHora.toLocal();
    final agora = DateTime.now();
    final isHoje = local.year == agora.year && local.month == agora.month && local.day == agora.day;
    final hh = local.hour.toString().padLeft(2, '0');
    final mm = local.minute.toString().padLeft(2, '0');
    if (isHoje) return 'hoje $hh:$mm';
    return '${local.day.toString().padLeft(2, '0')}/${local.month.toString().padLeft(2, '0')} $hh:$mm';
  }

  Future<void> _carregarPendenciasNotificacao() async {
    if (_loadingPendenciasNotificacao) return;
    setState(() {
      _loadingPendenciasNotificacao = true;
    });
    try {
      final repo = ref.read(insightsRepositoryProvider);
      final items = await repo.carregarPendenciasNotificacao();
      if (!mounted) return;
      setState(() {
        _pendenciasNotificacao = items;
      });
    } finally {
      if (mounted) {
        setState(() {
          _loadingPendenciasNotificacao = false;
        });
      }
    }
  }

  Future<void> _refreshTudo() async {
    await _sincronizarStatusNotificacoes(processQueue: true);
    await _carregarPendenciasNotificacao();
  }

  Future<void> _abrirConfiguracaoNotificacoes() async {
    if (defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await _notificationChannel.invokeMethod('openNotificationAccessSettings');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nao foi possivel abrir as configuracoes de notificacao.')),
      );
    }
  }

  Future<void> _sincronizarStatusNotificacoes({required bool processQueue}) async {
    if (defaultTargetPlatform != TargetPlatform.android) return;
    if (_loadingNotificationStatus) return;

    setState(() {
      _loadingNotificationStatus = true;
    });

    try {
      final enabled = await _notificationChannel.invokeMethod<bool>('isNotificationAccessEnabled') ?? false;
      final lastProcessed = await _notificationChannel.invokeMethod<String>('getLastNotificationProcessedAt');

      if (!mounted) return;
      setState(() {
        _notificationPermissionActive = enabled;
        _lastNotificationProcessedAt = lastProcessed;
      });

      if (enabled && processQueue) {
        await _processarNotificacoesPendentes();
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _notificationPermissionActive = false;
      });
    } finally {
      if (mounted) {
        setState(() {
          _loadingNotificationStatus = false;
        });
      }
    }
  }

  Future<void> _processarNotificacoesPendentes() async {
    if (_processingNotifications) return;
    _processingNotifications = true;

    try {
      final raw = await _notificationChannel.invokeMethod<List<dynamic>>('consumePendingFinancialNotifications');
      if (raw == null || raw.isEmpty) return;

      final repo = ref.read(insightsRepositoryProvider);
      var criadas = 0;
      for (final item in raw) {
        if (item is! Map) continue;
        final map = Map<String, dynamic>.from(item);
        final key = (map['notification_key'] ?? '').toString();
        final text = (map['text'] ?? '').toString().trim();
        if (key.isEmpty || text.isEmpty || _processedNotificationKeys.contains(key)) continue;

        final appName = (map['app_name'] ?? '').toString().trim();
        final title = (map['title'] ?? '').toString().trim();
        final packageName = (map['package_name'] ?? '').toString().trim();
        final subText = map['sub_text']?.toString();
        final postedAt = (map['posted_at'] ?? '').toString().trim();

        try {
          final response = await repo.interpretarTransacaoPorNotificacao(
            packageName: packageName,
            appName: appName.isEmpty ? packageName : appName,
            title: title,
            text: text,
            subText: subText,
            postedAt: postedAt.isEmpty ? DateTime.now().toIso8601String() : postedAt,
            notificationKey: key,
          );
          _processedNotificationKeys.add(key);
          if (response.created) {
            criadas += 1;
            final pendingId = response.pendingTransactionId;
            if (pendingId != null && pendingId.trim().isNotEmpty) {
              await LocalNotificationService.instance.showDetectedTransactionNotification(
                pendingTransactionId: pendingId,
                conta: appName.isEmpty ? packageName : appName,
                nome: _extrairNomeDaNotificacao(text),
                valor: _extrairValorDaNotificacao(text),
                confidence: response.confidence,
              );
            }
          }
        } catch (_) {
          // Ignora falhas pontuais para nao interromper o lote.
        }
      }

      if (!mounted) return;
      if (criadas > 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$criadas notificacoes processadas e enviadas para revisao.')),
        );
      }
      await _sincronizarStatusNotificacoes(processQueue: false);
      await _carregarPendenciasNotificacao();
    } finally {
      _processingNotifications = false;
    }
  }

  Future<void> _interpretarTexto() async {
    final texto = _textoController.text.trim();
    if (texto.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Digite uma transacao para interpretar.')),
      );
      return;
    }

    setState(() {
      _interpretando = true;
    });
    try {
      final repo = ref.read(insightsRepositoryProvider);
      final resultado = await repo.interpretarTransacaoPorTexto(texto);
      if (!mounted) return;
      setState(() {
        _resultado = resultado;
        _transcricaoAudio = null;
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensagemErro(error))));
    } finally {
      if (mounted) {
        setState(() {
          _interpretando = false;
        });
      }
    }
  }

  Future<void> _toggleGravacaoAudio() async {
    if (_gravandoAudio) {
      final stopResult = await _audioRecorder.stop();
      await _audioStreamSubscription?.cancel();
      _audioStreamSubscription = null;

      String? path;
      List<int>? bytes;
      String? nomeArquivo;
      if (kIsWeb) {
        if (_audioPcmBuffer.isNotEmpty) {
          bytes = _pcm16MonoToWav(
            pcmBytes: List<int>.from(_audioPcmBuffer),
            sampleRate: 16000,
            numChannels: 1,
          );
          nomeArquivo = 'gravacao.wav';
        }
      } else {
        path = stopResult;
        nomeArquivo = path == null ? null : 'gravacao.webm';
      }

      if (!mounted) return;
      setState(() {
        _gravandoAudio = false;
        _audioFilePath = path;
        _audioBytes = bytes;
        _audioFileName = nomeArquivo;
      });
      if (path != null || (bytes != null && bytes.isNotEmpty)) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Audio gravado com sucesso.')),
        );
      }
      return;
    }

    final permitido = await _audioRecorder.hasPermission();
    if (!permitido) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Permissao de microfone negada.')),
      );
      return;
    }

    if (kIsWeb) {
      _audioPcmBuffer.clear();
      final stream = await _audioRecorder.startStream(
        const RecordConfig(
          encoder: AudioEncoder.pcm16bits,
          sampleRate: 16000,
          numChannels: 1,
        ),
      );
      _audioStreamSubscription = stream.listen((chunk) {
        _audioPcmBuffer.addAll(chunk);
      });
    } else {
      await _audioRecorder.start(
        const RecordConfig(),
        path: 'alfred_audio.webm',
      );
    }

    if (!mounted) return;
    setState(() {
      _gravandoAudio = true;
      _audioFilePath = null;
      _audioBytes = null;
      _audioFileName = null;
    });
  }

  Future<void> _selecionarArquivoAudio() async {
    final selecionado = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['mp3', 'wav', 'm4a', 'ogg', 'webm'],
      withData: true,
    );
    if (selecionado == null || selecionado.files.isEmpty) return;

    final path = selecionado.files.single.path;
    final bytes = selecionado.files.single.bytes;
    final name = selecionado.files.single.name;

    if ((path == null || path.trim().isEmpty) && (bytes == null || bytes.isEmpty)) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nao foi possivel ler o arquivo selecionado.')),
      );
      return;
    }
    if (!mounted) return;
    setState(() {
      _audioFilePath = path;
      _audioBytes = bytes;
      _audioFileName = name;
    });
  }

  Future<void> _interpretarAudio() async {
    final path = _audioFilePath;
    final bytes = _audioBytes;
    if ((path == null || path.trim().isEmpty) && (bytes == null || bytes.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Grave ou selecione um audio antes de interpretar.')),
      );
      return;
    }

    setState(() {
      _interpretandoAudio = true;
    });
    try {
      final repo = ref.read(insightsRepositoryProvider);
      final audioResult = await repo.interpretarTransacaoPorAudio(
        filePath: path,
        fileBytes: bytes,
        fileName: _audioFileName,
      );
      if (!mounted) return;
      setState(() {
        _transcricaoAudio = audioResult.transcricao;
        _resultado = TextoParaTransacaoResponseDto(
          pendingTransactionId: audioResult.pendingTransactionId,
          transacaoSugerida: audioResult.transacaoSugerida,
        );
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensagemErro(error))));
    } finally {
      if (mounted) {
        setState(() {
          _interpretandoAudio = false;
        });
      }
    }
  }

  Future<void> _confirmarPendenciaNotificacao(
    PendingTransactionDto pendencia, {
    Map<String, dynamic>? payload,
  }) async {
    try {
      final repo = ref.read(insightsRepositoryProvider);
      await repo.confirmarTransacaoPendente(pendencia.id, payload: payload);
      if (!mounted) return;
      setState(() {
        _pendenciasNotificacao = _pendenciasNotificacao.where((item) => item.id != pendencia.id).toList();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Transacao confirmada com sucesso.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensagemErro(error))));
    }
  }

  Future<void> _ignorarPendenciaNotificacao(PendingTransactionDto pendencia) async {
    try {
      final repo = ref.read(insightsRepositoryProvider);
      await repo.ignorarTransacaoPendente(pendencia.id);
      if (!mounted) return;
      setState(() {
        _pendenciasNotificacao = _pendenciasNotificacao.where((item) => item.id != pendencia.id).toList();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sugestao ignorada.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensagemErro(error))));
    }
  }

  Future<void> _confirmar({Map<String, dynamic>? payload}) async {
    final resultado = _resultado;
    if (resultado == null) return;

    setState(() {
      _confirmando = true;
    });
    try {
      final repo = ref.read(insightsRepositoryProvider);
      await repo.confirmarTransacaoPendente(
        resultado.pendingTransactionId,
        payload: payload,
      );
      if (!mounted) return;
      setState(() {
        _resultado = null;
        _transcricaoAudio = null;
      });
      _textoController.clear();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Transacao confirmada com sucesso.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensagemErro(error))));
    } finally {
      if (mounted) {
        setState(() {
          _confirmando = false;
        });
      }
    }
  }

  Future<void> _ignorar() async {
    final resultado = _resultado;
    if (resultado == null) return;

    setState(() {
      _ignorando = true;
    });
    try {
      final repo = ref.read(insightsRepositoryProvider);
      await repo.ignorarTransacaoPendente(resultado.pendingTransactionId);
      if (!mounted) return;
      setState(() {
        _resultado = null;
        _transcricaoAudio = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sugestao ignorada.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensagemErro(error))));
    } finally {
      if (mounted) {
        setState(() {
          _ignorando = false;
        });
      }
    }
  }

  Future<void> _abrirEditorEConfirmar({
    required TransacaoSugeridaDto sugestao,
    required Future<void> Function(Map<String, dynamic> payload) onConfirmar,
  }) async {

    final nomeController = TextEditingController(text: sugestao.nome ?? '');
    final dataController = TextEditingController(text: sugestao.data ?? '');
    final valorController = TextEditingController(
      text: sugestao.valor != null ? sugestao.valor!.toStringAsFixed(2) : '',
    );
    final repo = ref.read(insightsRepositoryProvider);
    final categorias = await repo.carregarCategorias();
    if (!mounted) return;

    final tipos = <String>[
      'Despesa',
      'Receita',
      'Transferência',
      'Pagamento de Cartão',
      'Investimento',
    ];
    final contas = <String>[
      'Itaú CC',
      'Cartão Filippe',
      'Cartão Bianca',
      'Cartão Nath',
      'VR',
      'VA',
      'Nubank',
      'Inter',
      'Ion',
      'Nuinvest',
      '99Pay',
      'C6Invest',
      'InterInvest',
    ];

    String? tipoSelecionado = (sugestao.tipo != null && tipos.contains(sugestao.tipo)) ? sugestao.tipo : null;
    String? contaSelecionada = (sugestao.conta != null && contas.contains(sugestao.conta)) ? sugestao.conta : null;
    String? categoriaSelecionada = sugestao.categoria;

    List<String> categoriasPorTipo(String? tipo) {
      if (tipo == 'Despesa') return categorias.despesa;
      if (tipo == 'Receita') return categorias.receita;
      if (tipo == 'Investimento') return categorias.investimento;
      if (tipo == 'Transferência' || tipo == 'Pagamento de Cartão') return const ['Transferência'];
      return [...categorias.despesa, ...categorias.receita, ...categorias.investimento, 'Transferência'];
    }

    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setStateDialog) {
          final categoriasDisponiveis = categoriasPorTipo(tipoSelecionado);
          if (categoriaSelecionada != null && !categoriasDisponiveis.contains(categoriaSelecionada)) {
            categoriaSelecionada = null;
          }

          return AlertDialog(
            title: const Text('Editar antes de confirmar'),
            content: SingleChildScrollView(
              child: Column(
                children: [
                  TextField(controller: dataController, decoration: const InputDecoration(labelText: 'Data (YYYY-MM-DD)')),
                  DropdownButtonFormField<String>(
                    initialValue: tipoSelecionado,
                    decoration: const InputDecoration(labelText: 'Tipo'),
                    items: tipos.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                    onChanged: (value) => setStateDialog(() {
                      tipoSelecionado = value;
                    }),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: categoriaSelecionada,
                    decoration: const InputDecoration(labelText: 'Categoria'),
                    items: categoriasDisponiveis
                        .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                        .toList(),
                    onChanged: (value) => setStateDialog(() {
                      categoriaSelecionada = value;
                    }),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: contaSelecionada,
                    decoration: const InputDecoration(labelText: 'Conta'),
                    items: contas.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                    onChanged: (value) => setStateDialog(() {
                      contaSelecionada = value;
                    }),
                  ),
                  TextField(controller: nomeController, decoration: const InputDecoration(labelText: 'Nome')),
                  TextField(
                    controller: valorController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Valor'),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
              FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Confirmar')),
            ],
          );
        },
      ),
    );

    if (confirmado != true) return;

    final payload = <String, dynamic>{};
    if (dataController.text.trim().isNotEmpty) payload['data'] = dataController.text.trim();
    if (tipoSelecionado != null && tipoSelecionado!.trim().isNotEmpty) payload['tipo'] = tipoSelecionado!.trim();
    if (categoriaSelecionada != null && categoriaSelecionada!.trim().isNotEmpty) payload['categoria'] = categoriaSelecionada!.trim();
    if (contaSelecionada != null && contaSelecionada!.trim().isNotEmpty) payload['conta'] = contaSelecionada!.trim();
    if (nomeController.text.trim().isNotEmpty) payload['nome'] = nomeController.text.trim();
    if (valorController.text.trim().isNotEmpty) {
      final valor = double.tryParse(valorController.text.replaceAll(',', '.').trim());
      if (valor != null) payload['valor'] = valor;
    }
    await onConfirmar(payload);
  }

  Future<void> _editarEConfirmar() async {
    final resultado = _resultado;
    if (resultado == null) return;
    final sugestao = resultado.transacaoSugerida;
    await _abrirEditorEConfirmar(
      sugestao: sugestao,
      onConfirmar: (payload) => _confirmar(payload: payload),
    );
  }

  Widget _buildSugestaoCard(TextoParaTransacaoResponseDto resultado) {
    final s = resultado.transacaoSugerida;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Transacao sugerida', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            if (_transcricaoAudio != null && _transcricaoAudio!.trim().isNotEmpty) ...[
              Text('Transcricao: "${_transcricaoAudio!.trim()}"'),
              const SizedBox(height: 8),
            ],
            Text('Data: ${_formatarData(s.data)}'),
            Text('Tipo: ${s.tipo ?? '-'}'),
            Text('Categoria: ${s.categoria ?? '-'}'),
            Text('Conta: ${s.conta ?? '-'}'),
            Text('Nome: ${s.nome ?? '-'}'),
            Text('Valor: ${s.valor == null ? '-' : formatarMoeda(s.valor!)}'),
            Text('Confianca: ${_labelConfianca(s.confianca)} (${(s.confianca * 100).toStringAsFixed(0)}%)'),
            if (s.camposIncertos.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Campos incertos: ${s.camposIncertos.join(', ')}'),
            ],
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton(
                  onPressed: _confirmando ? null : () => _confirmar(),
                  child: _confirmando
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Confirmar'),
                ),
                OutlinedButton(
                  onPressed: _confirmando ? null : _editarEConfirmar,
                  child: const Text('Editar'),
                ),
                TextButton(
                  onPressed: _ignorando ? null : _ignorar,
                  child: _ignorando
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Ignorar'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Alfred IA')),
      body: RefreshIndicator(
        onRefresh: _refreshTudo,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
          const Text('Digite uma transacao:', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          TextField(
            controller: _textoController,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              hintText: 'gastei 42 reais no ifood ontem no nubank',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: _interpretando ? null : _interpretarTexto,
              icon: _interpretando
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.auto_awesome_outlined),
              label: const Text('Interpretar'),
            ),
          ),
          const SizedBox(height: 20),
          const Divider(),
          const SizedBox(height: 12),
          const Text('Audio', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                onPressed: _interpretandoAudio ? null : _toggleGravacaoAudio,
                icon: Icon(_gravandoAudio ? Icons.stop_circle_outlined : Icons.mic_none_outlined),
                label: Text(_gravandoAudio ? 'Parar gravacao' : 'Gravar audio'),
              ),
              OutlinedButton.icon(
                onPressed: _gravandoAudio || _interpretandoAudio ? null : _selecionarArquivoAudio,
                icon: const Icon(Icons.attach_file_outlined),
                label: const Text('Selecionar audio'),
              ),
              FilledButton.tonalIcon(
                onPressed: _gravandoAudio || _interpretandoAudio ? null : _interpretarAudio,
                icon: _interpretandoAudio
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.graphic_eq_outlined),
                label: const Text('Interpretar audio'),
              ),
            ],
          ),
          if (_audioFilePath != null || (_audioBytes != null && _audioBytes!.isNotEmpty)) ...[
            const SizedBox(height: 8),
            Text(
              'Audio pronto: ${_audioFileName ?? (_audioFilePath?.split(RegExp(r"[\\\\/]")).last ?? "gravacao.wav")}',
              style: const TextStyle(color: Colors.black54),
            ),
          ],
          const SizedBox(height: 16),
          if (_resultado != null) _buildSugestaoCard(_resultado!),
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 12),
          const Text('Transacoes detectadas automaticamente', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text(
            'Status: ${_notificationPermissionActive ? "Leitura de notificacoes ativa" : "Leitura de notificacoes inativa"}',
          ),
          const SizedBox(height: 4),
          Text('Ultima notificacao processada: ${_formatarUltimoProcessamento(_lastNotificationProcessedAt)}'),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _loadingNotificationStatus ? null : _abrirConfiguracaoNotificacoes,
            icon: const Icon(Icons.notifications_active_outlined),
            label: const Text('Ativar leitura de notificacoes'),
          ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () async {
                await LocalNotificationService.instance.showDebugNotification();
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Notificacao de teste enviada. Verifique a bandeja do Android.')),
                );
              },
              icon: const Icon(Icons.notification_add_outlined),
              label: const Text('Testar notificacao local'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Nenhuma transacao sera salva automaticamente. Todas as sugestoes passam por confirmacao, edicao ou ignorar.',
              style: TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 20),
            const Divider(),
            const SizedBox(height: 12),
            const Text('Pendencias detectadas por notificacao', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            if (_loadingPendenciasNotificacao)
              const Padding(
                padding: EdgeInsets.all(12),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_pendenciasNotificacao.isEmpty)
              const Text('Nenhuma pendencia de notificacao no momento.', style: TextStyle(color: Colors.black54))
            else
              ..._pendenciasNotificacao.map(_buildPendenciaNotificacaoCard),
          ],
        ),
      ),
    );
  }

  Widget _buildPendenciaNotificacaoCard(PendingTransactionDto pendencia) {
    final s = pendencia.transacaoSugerida;
    final notificacao = pendencia.suggestedPayload['notificacao'];
    final appName = notificacao is Map ? (notificacao['app_name']?.toString() ?? 'App') : 'App';
    final nome = s?.nome?.trim().isNotEmpty == true ? s!.nome!.trim() : 'Transacao detectada';
    final tipo = s?.tipo ?? '-';
    final categoria = s?.categoria ?? '-';
    final conta = s?.conta ?? '-';
    final valor = s?.valor;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(nome),
              subtitle: Text('$tipo - $categoria - $conta'),
              trailing: Text(valor == null ? '-' : formatarMoeda(valor)),
            ),
            const SizedBox(height: 4),
            Text(
              'Detectado por notificacao $appName - ${_formatarDataHoraDeteccao(pendencia.createdAt)}',
              style: const TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton(
                  onPressed: () => _confirmarPendenciaNotificacao(pendencia),
                  child: const Text('Confirmar'),
                ),
                OutlinedButton(
                  onPressed: s == null
                      ? null
                      : () => _abrirEditorEConfirmar(
                            sugestao: s,
                            onConfirmar: (payload) => _confirmarPendenciaNotificacao(pendencia, payload: payload),
                          ),
                  child: const Text('Editar'),
                ),
                TextButton(
                  onPressed: () => _ignorarPendenciaNotificacao(pendencia),
                  child: const Text('Ignorar'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
