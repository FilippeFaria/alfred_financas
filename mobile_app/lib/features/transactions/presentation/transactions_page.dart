import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/utils/formatters.dart';
import '../data/transaction_models.dart';
import '../data/transactions_repository.dart';

const _nomesMeses = <String>[
  'Janeiro',
  'Fevereiro',
  'Março',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
];

class TransactionsPage extends ConsumerStatefulWidget {
  const TransactionsPage({super.key});

  @override
  ConsumerState<TransactionsPage> createState() => _TransactionsPageState();
}

class _TransactionsPageState extends ConsumerState<TransactionsPage> {
  final ScrollController _scrollController = ScrollController();
  static const Color _positivoColor = Color(0xFF0E7A6D);
  static const Color _negativoColor = Color(0xFFB76E00);

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    Future<void>.microtask(() => ref.read(transactionsNotifierProvider.notifier).inicializar());
  }

  void _onScroll() {
    if (!_scrollController.hasClients) {
      return;
    }
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 280) {
      ref.read(transactionsNotifierProvider.notifier).carregarMais();
    }
  }

  Future<void> _abrirCadastro() async {
    final salvou = await context.push<bool>('/transactions/form');
    if (salvou == true && mounted) {
      await ref.read(transactionsNotifierProvider.notifier).recarregar();
    }
  }

  Future<void> _abrirEdicao(TransacaoItem item) async {
    final salvou = await context.push<bool>(
      '/transactions/form',
      extra: TransactionsFormArgs(transacaoInicial: item),
    );
    if (salvou == true && mounted) {
      await ref.read(transactionsNotifierProvider.notifier).recarregar();
    }
  }

  Future<void> _confirmarExclusao(TransacaoItem item) async {
    final confirmar = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Excluir transação'),
        content: Text('Deseja excluir "${item.nome}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Excluir')),
        ],
      ),
    );
    if (confirmar != true) return;
    try {
      await ref.read(transactionsNotifierProvider.notifier).excluirTransacao(item.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Transação excluída.')));
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erro ao excluir: $error')));
    }
  }

  Future<void> _alternarDesconsiderar(TransacaoItem item) async {
    try {
      await ref.read(transactionsNotifierProvider.notifier).atualizarFlagsTransacao(
            item.id,
            desconsiderar: !item.desconsiderar,
          );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erro ao atualizar: $error')));
    }
  }

  Future<void> _alternarGrandeTransacao(TransacaoItem item) async {
    final marcada = (item.tag ?? '').toUpperCase() == 'GRANDE_TRANSACAO';
    try {
      await ref.read(transactionsNotifierProvider.notifier).atualizarFlagsTransacao(
            item.id,
            grandeTransacao: !marcada,
          );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erro ao atualizar: $error')));
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(transactionsNotifierProvider);
    final notifier = ref.read(transactionsNotifierProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('Transações')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _abrirCadastro,
        icon: const Icon(Icons.add),
        label: const Text('Novo'),
      ),
      body: RefreshIndicator(
        onRefresh: notifier.recarregar,
        child: ListView(
          controller: _scrollController,
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            _FiltersCard(
              state: state,
              onApply: notifier.atualizarFiltros,
            ),
            const SizedBox(height: 12),
            if (state.isLoading && state.items.isEmpty) ...const [
              _LoadingCard(),
              SizedBox(height: 8),
              _LoadingCard(),
              SizedBox(height: 8),
              _LoadingCard(),
            ] else if (state.errorMessage != null && state.items.isEmpty) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      const Text('Falha ao carregar transações.'),
                      const SizedBox(height: 8),
                      Text(state.errorMessage!, textAlign: TextAlign.center),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: notifier.recarregar,
                        child: const Text('Tentar novamente'),
                      ),
                    ],
                  ),
                ),
              ),
            ] else ...[
              _ResumoCard(total: state.total, exibindo: state.items.length),
              const SizedBox(height: 8),
              ...state.items.map(
                (item) {
                  final isPositivo = item.valor >= 0;
                  final cor = isPositivo ? _positivoColor : _negativoColor;
                  final categoria = item.categoria.trim().isEmpty ? 'Sem categoria' : item.categoria;

                  return Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: cor.withValues(alpha: 0.12),
                        child: Icon(
                          isPositivo ? Icons.arrow_upward : Icons.arrow_downward,
                          color: cor,
                        ),
                      ),
                      title: Text(item.nome),
                      subtitle: Text(
                        '$categoria • ${item.conta} • ${item.tipo} • ${formatarDataCurta(item.data)}',
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            formatarMoeda(item.valor),
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              color: cor,
                            ),
                          ),
                          PopupMenuButton<String>(
                            onSelected: (value) async {
                              if (value == 'desconsiderar') {
                                await _alternarDesconsiderar(item);
                              } else if (value == 'grande') {
                                await _alternarGrandeTransacao(item);
                              } else if (value == 'editar') {
                                await _abrirEdicao(item);
                              } else if (value == 'excluir') {
                                await _confirmarExclusao(item);
                              }
                            },
                            itemBuilder: (context) {
                              final marcada = (item.tag ?? '').toUpperCase() == 'GRANDE_TRANSACAO';
                              return [
                                PopupMenuItem<String>(
                                  value: 'desconsiderar',
                                  child: Text(item.desconsiderar ? 'Considerar novamente' : 'Desconsiderar'),
                                ),
                                PopupMenuItem<String>(
                                  value: 'grande',
                                  child: Text(marcada ? 'Remover grande transação' : 'Grande transação'),
                                ),
                                const PopupMenuItem<String>(value: 'editar', child: Text('Editar')),
                                const PopupMenuItem<String>(value: 'excluir', child: Text('Excluir')),
                              ];
                            },
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
              if (state.isLoadingMore)
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                ),
              if (!state.hasMore && state.items.isNotEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  child: Center(child: Text('Fim do extrato')),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class TransactionsFormArgs {
  const TransactionsFormArgs({this.transacaoInicial});

  final TransacaoItem? transacaoInicial;
}

class TransactionsFormPage extends ConsumerStatefulWidget {
  const TransactionsFormPage({super.key, this.transacaoInicial});

  final TransacaoItem? transacaoInicial;

  @override
  ConsumerState<TransactionsFormPage> createState() => _TransactionsFormPageState();
}

class _TransactionsFormPageState extends ConsumerState<TransactionsFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _nomeController = TextEditingController();
  final _valorController = TextEditingController();
  final _obsController = TextEditingController();
  final _parcelasController = TextEditingController(text: '2');
  late final Future<CadastroTransacaoOptions> _opcoesFuture;
  bool _desconsiderar = false;
  bool _isSaving = false;
  bool _hasChanges = false;
  bool _snapshotInicialCapturado = false;
  String _snapshotNome = '';
  String _snapshotValor = '';
  String _snapshotObs = '';
  String _snapshotTipo = 'Despesa';
  String? _snapshotCategoria;
  String? _snapshotConta;
  String? _snapshotContaDestino;
  String? _snapshotCartaoSelecionado;
  String? _snapshotTipoInvestimentoNome;
  bool _snapshotDesconsiderar = false;
  bool _snapshotParcelado = false;
  String _snapshotData = '';
  String? _categoriaEfetivaAtual;
  String? _contaEfetivaAtual;
  String? _contaDestinoEfetivaAtual;
  DateTime _data = DateTime.now();
  String _tipo = 'Despesa';
  String? _categoria;
  String? _conta;
  String? _contaDestino;
  String? _cartaoSelecionado;
  String? _tipoInvestimentoNome;
  bool _parcelado = false;
  bool get _modoEdicao => widget.transacaoInicial != null;

  String _formatarDataDiaMesAno(DateTime data) {
    final dia = data.day.toString().padLeft(2, '0');
    final mes = data.month.toString().padLeft(2, '0');
    return '$dia/$mes/${data.year}';
  }

  void _marcarAlteracao() {
    if (_hasChanges || _isSaving || !mounted) return;
    setState(() => _hasChanges = true);
  }

  void _capturarSnapshotInicial({
    required String categoriaAtual,
    required String contaAtual,
    required String contaDestinoAtual,
  }) {
    if (_snapshotInicialCapturado) return;
    _snapshotNome = _nomeController.text;
    _snapshotValor = _valorController.text;
    _snapshotObs = _obsController.text;
    _snapshotTipo = _tipo;
    _snapshotCategoria = _categoria ?? categoriaAtual;
    _snapshotConta = _conta ?? contaAtual;
    _snapshotContaDestino = _contaDestino ?? contaDestinoAtual;
    _snapshotCartaoSelecionado = _cartaoSelecionado;
    _snapshotTipoInvestimentoNome = _tipoInvestimentoNome;
    _snapshotDesconsiderar = _desconsiderar;
    _snapshotParcelado = _parcelado;
    _snapshotData = _data.toIso8601String();
    _snapshotInicialCapturado = true;
  }

  bool _temAlteracoesRelevantes() {
    if (!_snapshotInicialCapturado) return false;
    return _nomeController.text != _snapshotNome ||
        _valorController.text != _snapshotValor ||
        _obsController.text != _snapshotObs ||
        _tipo != _snapshotTipo ||
        _categoriaEfetivaAtual != _snapshotCategoria ||
        _contaEfetivaAtual != _snapshotConta ||
        _contaDestinoEfetivaAtual != _snapshotContaDestino ||
        _cartaoSelecionado != _snapshotCartaoSelecionado ||
        _tipoInvestimentoNome != _snapshotTipoInvestimentoNome ||
        _desconsiderar != _snapshotDesconsiderar ||
        _parcelado != _snapshotParcelado ||
        _data.toIso8601String() != _snapshotData;
  }

  Future<bool> _confirmarDescarteSeNecessario() async {
    if (_isSaving || !_temAlteracoesRelevantes()) return true;
    final descartar = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Descartar alterações?'),
        content: const Text('Você tem alterações não salvas. Deseja descartar e sair?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Continuar editando'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Descartar'),
          ),
        ],
      ),
    );
    return descartar == true;
  }

  @override
  void initState() {
    super.initState();
    final notifier = ref.read(transactionsNotifierProvider.notifier);
    _opcoesFuture = notifier.carregarOpcoesCadastro();
    final tx = widget.transacaoInicial;
    if (tx != null) {
      _nomeController.text = tx.nome;
      _valorController.text = tx.valor.abs().toStringAsFixed(2);
      _obsController.text = tx.obs;
      _tipo = tx.tipo;
      _categoria = tx.categoria;
      _conta = tx.conta;
      _desconsiderar = tx.desconsiderar;
      _data = _parseDataBr(tx.data) ?? DateTime.now();
    }

    _nomeController.addListener(_marcarAlteracao);
    _valorController.addListener(_marcarAlteracao);
    _obsController.addListener(_marcarAlteracao);
    _parcelasController.addListener(_marcarAlteracao);
  }

  @override
  void dispose() {
    _nomeController.dispose();
    _valorController.dispose();
    _obsController.dispose();
    _parcelasController.dispose();
    super.dispose();
  }

  List<String> _categoriasDisponiveis(CadastroTransacaoOptions opcoes) {
    return _categoriasPorTipo(opcoes).toSet().toList();
  }

  List<String> _contasDisponiveis(CadastroTransacaoOptions opcoes) {
    if (_tipo == 'Investimento') {
      return {...opcoes.contas, ...opcoes.contasInvestimento}.toList();
    }
    return opcoes.contas.toSet().toList();
  }

  List<String> _contasDestinoDisponiveis(CadastroTransacaoOptions opcoes) {
    return (_tipo == 'Investimento' ? [...opcoes.contas, ...opcoes.contasInvestimento] : opcoes.contas)
        .toSet()
        .toList();
  }

  String? _categoriaSelecionadaAtual(CadastroTransacaoOptions opcoes) {
    final categorias = _categoriasDisponiveis(opcoes);
    if (categorias.isEmpty) {
      return null;
    }
    if (_categoria != null && categorias.contains(_categoria)) {
      return _categoria;
    }
    return categorias.first;
  }

  String? _contaSelecionadaAtual(CadastroTransacaoOptions opcoes) {
    final contas = _contasDisponiveis(opcoes);
    if (contas.isEmpty) {
      return null;
    }
    if (_conta != null && contas.contains(_conta)) {
      return _conta;
    }
    return contas.first;
  }

  String? _contaDestinoSelecionadaAtual(CadastroTransacaoOptions opcoes) {
    final contasDestino = _contasDestinoDisponiveis(opcoes);
    if (contasDestino.isEmpty) {
      return null;
    }
    if (_contaDestino != null && contasDestino.contains(_contaDestino)) {
      return _contaDestino;
    }
    return contasDestino.length > 1 ? contasDestino[1] : contasDestino.first;
  }

  Future<void> _selecionarData() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _data,
      firstDate: DateTime(2015, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (picked != null) {
      setState(() {
        _data = picked;
        _hasChanges = true;
      });
    }
  }

  DateTime? _parseDataBr(String raw) {
    try {
      final dataPart = raw.split(' ').first;
      final partes = dataPart.split('/');
      if (partes.length != 3) return null;
      final dia = int.parse(partes[0]);
      final mes = int.parse(partes[1]);
      final ano = int.parse(partes[2]);
      return DateTime(ano, mes, dia);
    } catch (_) {
      return null;
    }
  }

  List<String> _categoriasPorTipo(CadastroTransacaoOptions opcoes) {
    if (_tipo == 'Despesa') {
      return opcoes.categoriasDespesa;
    }
    if (_tipo == 'Receita') {
      return opcoes.categoriasReceita;
    }
    if (_tipo == 'Investimento') {
      return opcoes.categoriasInvestimento;
    }
    if (_tipo == 'Transferência') {
      return const ['Transferência'];
    }
    return const ['Outros'];
  }

  Future<void> _salvar(
    CadastroTransacaoOptions opcoes, {
    bool ignorarDuplicata = false,
  }) async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    final notifier = ref.read(transactionsNotifierProvider.notifier);
    final valorBruto = double.tryParse(_valorController.text.replaceAll(',', '.')) ?? 0;

    if (valorBruto <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Informe um valor maior que zero.')),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      final categoriaAtual = _categoriaSelecionadaAtual(opcoes);
      final contaAtual = _contaSelecionadaAtual(opcoes);
      final contaDestinoAtual = _contaDestinoSelecionadaAtual(opcoes);

      if (_modoEdicao && (_tipo == 'Transferência' || _tipo == 'Investimento' || _tipo == 'Pagamento de Cartão')) {
        throw Exception('Edição para este tipo ainda não está disponível. Exclua e recrie.');
      }

      if (_tipo == 'Transferência' || _tipo == 'Investimento') {
        if (contaAtual == null || contaDestinoAtual == null || contaDestinoAtual == contaAtual) {
          throw Exception('Selecione conta origem e destino diferentes.');
        }
        final contaOrigem = contaAtual;
        final contaDestino = contaDestinoAtual;
        final nome = _tipo == 'Investimento' ? (_tipoInvestimentoNome ?? 'Aplicação') : 'Transferência';
        final categoria = _tipo == 'Transferência' ? 'Transferência' : (categoriaAtual ?? '');
        await notifier.cadastrarTransacao(
          CadastroTransacaoInput(
            nome: nome,
            tipo: _tipo,
            valor: -valorBruto,
            categoria: categoria,
            conta: contaOrigem,
            data: _data,
            obs: _obsController.text.trim(),
          ),
          ignorarDuplicata: ignorarDuplicata,
        );
        await notifier.cadastrarTransacao(
          CadastroTransacaoInput(
            nome: nome,
            tipo: _tipo,
            valor: valorBruto,
            categoria: categoria,
            conta: contaDestino,
            data: _data,
            obs: _obsController.text.trim(),
          ),
          ignorarDuplicata: ignorarDuplicata,
        );
      } else if (_tipo == 'Pagamento de Cartão') {
        if (_cartaoSelecionado == null) {
          throw Exception('Selecione o cartão.');
        }
        final cartao = _cartaoSelecionado!;
        if (opcoes.cartoesPagamentoTransferencia.contains(cartao)) {
        await notifier.cadastrarTransacao(
          CadastroTransacaoInput(
            nome: 'Pagamento $cartao',
            tipo: 'Transferência',
            valor: -valorBruto,
            categoria: 'Transferência',
            conta: contaAtual ?? 'Itaú CC',
            data: _data,
            obs: _obsController.text.trim(),
          ),
          ignorarDuplicata: ignorarDuplicata,
        );
          await notifier.cadastrarTransacao(
            CadastroTransacaoInput(
              nome: 'Pagamento $cartao',
            tipo: 'Transferência',
            valor: valorBruto,
            categoria: 'Transferência',
            conta: cartao,
            data: _data,
            obs: _obsController.text.trim(),
          ),
            ignorarDuplicata: ignorarDuplicata,
        );
        } else {
          await notifier.cadastrarTransacao(
            CadastroTransacaoInput(
            nome: 'Pagamento $cartao',
            tipo: 'Despesa',
            valor: -valorBruto,
            categoria: 'Outros',
            conta: contaAtual ?? 'Itaú CC',
            data: _data,
            obs: _obsController.text.trim(),
            desconsiderar: true,
          ),
            ignorarDuplicata: ignorarDuplicata,
          );
        }
      } else {
        final valorAjustado = _tipo == 'Despesa' ? -valorBruto : valorBruto;
        final parcelas = _tipo == 'Despesa' && _parcelado
            ? int.tryParse(_parcelasController.text.trim())
            : null;
        final input = CadastroTransacaoInput(
          nome: _nomeController.text.trim(),
          tipo: _tipo,
          valor: valorAjustado,
          categoria: categoriaAtual ?? '',
          conta: contaAtual ?? '',
          data: _data,
          obs: _obsController.text.trim(),
          desconsiderar: _desconsiderar,
          parcelas: parcelas,
        );
        if (_modoEdicao) {
          await notifier.editarTransacao(widget.transacaoInicial!.id, input);
        } else {
          await notifier.cadastrarTransacao(
            input,
            ignorarDuplicata: ignorarDuplicata,
          );
        }
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            behavior: SnackBarBehavior.floating,
            margin: const EdgeInsets.fromLTRB(16, 12, 16, 96),
            content: Text(_modoEdicao ? 'Transação atualizada com sucesso.' : 'Transação salva com sucesso.'),
          ),
        );
        _hasChanges = false;
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (!ignorarDuplicata && error is ApiException && error.code == 'DUPLICATA_TRANSACAO') {
        final confirmar = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Transação duplicada'),
            content: const Text('Já existe uma transação com mesmo valor, conta e data. Deseja adicionar mesmo assim?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Cancelar'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Adicionar mesmo assim'),
              ),
            ],
          ),
        );
        if (confirmar == true && mounted) {
          await _salvar(opcoes, ignorarDuplicata: true);
        }
        return;
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Não foi possível salvar: $error')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop) return;
        _confirmarDescarteSeNecessario().then((deveSair) {
          if (deveSair && context.mounted) {
            Navigator.of(context).pop(false);
          }
        });
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(_modoEdicao ? 'Editar transação' : 'Nova transação'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () async {
              if (await _confirmarDescarteSeNecessario() && context.mounted) {
                Navigator.of(context).pop(false);
              }
            },
          ),
        ),
        body: FutureBuilder<CadastroTransacaoOptions>(
          future: _opcoesFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return Center(
                child: Text('Falha ao carregar opções: ${snapshot.error}'),
              );
            }
            final opcoes = snapshot.data!;
            final categorias = _categoriasDisponiveis(opcoes);
            final contas = _contasDisponiveis(opcoes);
            final contasDestino = _contasDestinoDisponiveis(opcoes);
            final categoriaAtual = _categoriaSelecionadaAtual(opcoes);
            final contaAtual = _contaSelecionadaAtual(opcoes);
            final contaDestinoAtual = _contaDestinoSelecionadaAtual(opcoes);
            _categoriaEfetivaAtual = categoriaAtual;
            _contaEfetivaAtual = contaAtual;
            _contaDestinoEfetivaAtual = contaDestinoAtual;
            _tipoInvestimentoNome ??= 'Aplicação';
            _cartaoSelecionado ??= opcoes.cartoesPagamento.isNotEmpty ? opcoes.cartoesPagamento.first : null;
            _capturarSnapshotInicial(
              categoriaAtual: categoriaAtual ?? '',
              contaAtual: contaAtual ?? '',
              contaDestinoAtual: contaDestinoAtual ?? '',
            );

            return Padding(
              padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + bottom),
              child: SingleChildScrollView(
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  DropdownButtonFormField<String>(
                    initialValue: _tipo,
                    decoration: const InputDecoration(labelText: 'Tipo'),
                    items: const [
                      DropdownMenuItem(value: 'Receita', child: Text('Receita')),
                      DropdownMenuItem(value: 'Despesa', child: Text('Despesa')),
                      DropdownMenuItem(value: 'Transferência', child: Text('Transferência')),
                      DropdownMenuItem(value: 'Investimento', child: Text('Investimento')),
                      DropdownMenuItem(value: 'Pagamento de Cartão', child: Text('Pagamento de Cartão')),
                    ],
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() {
                        _tipo = value;
                        _hasChanges = true;
                        if (_tipo != 'Despesa' && _tipo != 'Investimento' && _tipo != 'Transferência') {
                          _parcelado = false;
                          _desconsiderar = false;
                        }
                        if (_tipo == 'Transferência' || _tipo == 'Investimento') {
                          _categoria = null;
                        }
                        if (_tipo != 'Despesa') {
                          _parcelado = false;
                        }
                      });
                    },
                  ),
                  const SizedBox(height: 8),
                  if (_tipo != 'Pagamento de Cartão')
                    TextFormField(
                      controller: _nomeController,
                      decoration: const InputDecoration(labelText: 'Descrição'),
                      validator: (value) {
                        if (_tipo == 'Transferência' || _tipo == 'Investimento') {
                          return null;
                        }
                        if (value == null || value.trim().isEmpty) {
                          return 'Informe a descrição.';
                        }
                        return null;
                      },
                    ),
                if (_tipo == 'Pagamento de Cartão')
                  DropdownButtonFormField<String>(
                      initialValue: _cartaoSelecionado,
                      decoration: const InputDecoration(labelText: 'Cartão'),
                      items: opcoes.cartoesPagamento
                          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                          .toList(),
                      onChanged: (value) => setState(() {
                        _cartaoSelecionado = value;
                        _hasChanges = true;
                      }),
                    ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _valorController,
                    decoration: const InputDecoration(labelText: 'Valor'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (value) {
                      final parsed = double.tryParse((value ?? '').replaceAll(',', '.'));
                      if (parsed == null || parsed <= 0) {
                        return 'Informe um valor válido.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 8),
                  if (_tipo == 'Investimento')
                    DropdownButtonFormField<String>(
                      initialValue: _tipoInvestimentoNome,
                      decoration: const InputDecoration(labelText: 'Tipo transação'),
                      items: const [
                        DropdownMenuItem(value: 'Aplicação', child: Text('Aplicação')),
                        DropdownMenuItem(value: 'Resgate', child: Text('Resgate')),
                      ],
                      onChanged: (value) => setState(() {
                        _tipoInvestimentoNome = value;
                        _hasChanges = true;
                      }),
                    ),
                  if (_tipo != 'Pagamento de Cartão')
                    DropdownButtonFormField<String>(
                      initialValue: categoriaAtual,
                      decoration: const InputDecoration(labelText: 'Categoria'),
                      items: categorias
                          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                          .toList(),
                      onChanged: (value) => setState(() {
                        _categoria = value;
                        _hasChanges = true;
                      }),
                    ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    initialValue: contaAtual,
                    decoration: InputDecoration(
                      labelText: _tipo == 'Transferência' || _tipo == 'Investimento'
                          ? 'Conta origem'
                          : 'Conta',
                    ),
                    items: contas.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                    onChanged: (value) => setState(() {
                      _conta = value;
                      _hasChanges = true;
                    }),
                  ),
                  if (_tipo == 'Transferência' || _tipo == 'Investimento') ...[
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      initialValue: contaDestinoAtual,
                      decoration: const InputDecoration(labelText: 'Conta destino'),
                      items: contasDestino.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                      onChanged: (value) => setState(() {
                        _contaDestino = value;
                        _hasChanges = true;
                      }),
                    ),
                  ],
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _selecionarData,
                    icon: const Icon(Icons.calendar_today_outlined),
                    label: Text('Data: ${_formatarDataDiaMesAno(_data)}'),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _obsController,
                    decoration: const InputDecoration(labelText: 'Comentário'),
                  ),
                  if (_tipo == 'Despesa') ...[
                    const SizedBox(height: 8),
                    SwitchListTile(
                      value: _desconsiderar,
                      onChanged: (value) => setState(() {
                        _desconsiderar = value;
                        _hasChanges = true;
                      }),
                      title: const Text('Desconsiderar na análise'),
                    ),
                    SwitchListTile(
                      value: _parcelado,
                      onChanged: (value) => setState(() {
                        _parcelado = value;
                        _hasChanges = true;
                      }),
                      title: const Text('Compra parcelada'),
                    ),
                    if (_parcelado)
                      TextFormField(
                        controller: _parcelasController,
                        decoration: const InputDecoration(labelText: 'Parcelas'),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (!_parcelado) return null;
                          final n = int.tryParse(value ?? '');
                          if (n == null || n < 1) {
                            return 'Informe quantidade de parcelas.';
                          }
                          return null;
                        },
                      ),
                  ],
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _isSaving ? null : () => _salvar(opcoes),
                      child: Text(_isSaving ? 'Salvando...' : 'Salvar'),
                    ),
                  ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _FiltersCard extends StatefulWidget {
  const _FiltersCard({
    required this.state,
    required this.onApply,
  });

  final TransactionsState state;
  final Future<void> Function(TransactionsFilters) onApply;

  @override
  State<_FiltersCard> createState() => _FiltersCardState();
}

class _FiltersCardState extends State<_FiltersCard> {
  int? _mes;
  int? _ano;
  String? _categoria;
  String? _conta;
  String? _tipo;

  @override
  void initState() {
    super.initState();
    _carregarEstado(widget.state.filtros);
  }

  @override
  void didUpdateWidget(covariant _FiltersCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.state.filtros != widget.state.filtros) {
      _carregarEstado(widget.state.filtros);
    }
  }

  void _carregarEstado(TransactionsFilters filtros) {
    final mesReferencia = filtros.mesReferencia;
    if (mesReferencia != null && mesReferencia.contains('-')) {
      final partes = mesReferencia.split('-');
      _ano = int.tryParse(partes[0]);
      _mes = int.tryParse(partes[1]);
    } else {
      _mes = null;
      _ano = null;
    }
    _categoria = filtros.categoria;
    _conta = filtros.conta;
    _tipo = filtros.tipo;
  }

  List<int> _anosDisponiveis() {
    final anoAtual = DateTime.now().year;
    return [for (var ano = 2015; ano <= anoAtual + 1; ano++) ano];
  }

  String _mesLabel(int mes) => _nomesMeses[mes - 1];

  String? _mesReferenciaSelecionada() {
    if (_mes == null || _ano == null) {
      return null;
    }
    return '${_ano!.toString().padLeft(4, '0')}-${_mes!.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final opcoes = widget.state.opcoes;

    return Card(
      child: ExpansionTile(
        title: const Text('Filtros', style: TextStyle(fontWeight: FontWeight.w700)),
        initiallyExpanded: false,
        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        children: [
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<int?>(
                    initialValue: _mes,
                    decoration: const InputDecoration(labelText: 'Mês'),
                    items: [
                      const DropdownMenuItem<int?>(value: null, child: Text('Todos')),
                      ...List.generate(
                        12,
                        (index) => DropdownMenuItem<int?>(
                          value: index + 1,
                          child: Text(_mesLabel(index + 1)),
                        ),
                      ),
                    ],
                    onChanged: (value) => setState(() => _mes = value),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<int?>(
                    initialValue: _ano,
                    decoration: const InputDecoration(labelText: 'Ano'),
                    items: [
                      const DropdownMenuItem<int?>(value: null, child: Text('Todos')),
                      ..._anosDisponiveis().map(
                        (ano) => DropdownMenuItem<int?>(
                          value: ano,
                          child: Text(ano.toString()),
                        ),
                      ),
                    ],
                    onChanged: (value) => setState(() => _ano = value),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              initialValue: _categoria,
              decoration: const InputDecoration(labelText: 'Categoria'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Todas')),
                ...?opcoes?.categorias.map(
                  (item) => DropdownMenuItem<String?>(value: item, child: Text(item)),
                ),
              ],
              onChanged: (value) => setState(() => _categoria = value),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              initialValue: _conta,
              decoration: const InputDecoration(labelText: 'Conta'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Todas')),
                ...?opcoes?.contas.map(
                  (item) => DropdownMenuItem<String?>(value: item, child: Text(item)),
                ),
              ],
              onChanged: (value) => setState(() => _conta = value),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              initialValue: _tipo,
              decoration: const InputDecoration(labelText: 'Tipo'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Todos')),
                ...?opcoes?.tipos.map(
                  (item) => DropdownMenuItem<String?>(value: item, child: Text(item)),
                ),
              ],
              onChanged: (value) => setState(() => _tipo = value),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () async {
                      final agora = DateTime.now();
                      final mesReferenciaAtual =
                          '${agora.year.toString().padLeft(4, '0')}-${agora.month.toString().padLeft(2, '0')}';
                      setState(() {
                        _mes = agora.month;
                        _ano = agora.year;
                        _categoria = null;
                        _conta = null;
                        _tipo = null;
                      });
                      await widget.onApply(TransactionsFilters(mesReferencia: mesReferenciaAtual));
                    },
                    child: const Text('Limpar'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilledButton(
                    onPressed: () async {
                      final mesReferencia = _mesReferenciaSelecionada();
                      await widget.onApply(
                        widget.state.filtros.copyWith(
                          mesReferencia: mesReferencia,
                          categoria: _categoria,
                          conta: _conta,
                          tipo: _tipo,
                          clearMesReferencia: mesReferencia == null,
                          clearCategoria: _categoria == null,
                          clearConta: _conta == null,
                          clearTipo: _tipo == null,
                        ),
                      );
                    },
                    child: const Text('Aplicar'),
                  ),
                ),
              ],
            ),
          ],
        ),
    );
  }
}

class _ResumoCard extends StatelessWidget {
  const _ResumoCard({required this.total, required this.exibindo});

  final int total;
  final int exibindo;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.receipt_long_outlined),
        title: const Text('Resumo do extrato'),
        subtitle: Text('Exibindo $exibindo de $total registros'),
      ),
    );
  }
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 76,
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(12),
      ),
    );
  }
}
