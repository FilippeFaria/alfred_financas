import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/categorias_dto.dart';
import '../../../core/network/dto/criar_transacao_dto.dart';
import '../../../core/network/dto/transacao_dto.dart';
import 'transaction_models.dart';

const _filtrosKey = 'transactions_filters_v2';

final transactionsRepositoryProvider = Provider<TransactionsRepository>((ref) {
  return TransactionsRepository(ref.watch(alfredApiClientProvider));
});

class TransactionsFilters {
  const TransactionsFilters({
    this.mesReferencia,
    this.categoria,
    this.conta,
    this.tipo,
  });

  final String? mesReferencia;
  final String? categoria;
  final String? conta;
  final String? tipo;

  TransactionsFilters copyWith({
    String? mesReferencia,
    String? categoria,
    String? conta,
    String? tipo,
    bool clearMesReferencia = false,
    bool clearCategoria = false,
    bool clearConta = false,
    bool clearTipo = false,
  }) {
    return TransactionsFilters(
      mesReferencia: clearMesReferencia ? null : (mesReferencia ?? this.mesReferencia),
      categoria: clearCategoria ? null : (categoria ?? this.categoria),
      conta: clearConta ? null : (conta ?? this.conta),
      tipo: clearTipo ? null : (tipo ?? this.tipo),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'mes_referencia': mesReferencia,
      'categoria': categoria,
      'conta': conta,
      'tipo': tipo,
    };
  }

  factory TransactionsFilters.fromMap(Map<String, dynamic> map) {
    return TransactionsFilters(
      mesReferencia: _inferirMesReferencia(map),
      categoria: map['categoria']?.toString(),
      conta: map['conta']?.toString(),
      tipo: map['tipo']?.toString(),
    );
  }

  static String? _inferirMesReferencia(Map<String, dynamic> map) {
    final valorDireto = map['mes_referencia']?.toString();
    if (valorDireto != null && valorDireto.trim().isNotEmpty) {
      return valorDireto.trim();
    }

    final dataInicio = _normalizarMesReferencia(map['data_inicio']?.toString());
    final dataFim = _normalizarMesReferencia(map['data_fim']?.toString());

    if (dataInicio != null && dataFim != null) {
      return dataInicio == dataFim ? dataInicio : null;
    }
    return dataInicio ?? dataFim;
  }

  static String? _normalizarMesReferencia(String? valor) {
    if (valor == null || valor.trim().isEmpty) {
      return null;
    }
    final parsed = DateTime.tryParse(valor.trim());
    if (parsed == null) {
      return null;
    }
    return '${parsed.year}-${parsed.month.toString().padLeft(2, '0')}';
  }

  static String mesReferenciaAtual() {
    final agora = DateTime.now();
    return '${agora.year.toString().padLeft(4, '0')}-${agora.month.toString().padLeft(2, '0')}';
  }

  static TransactionsFilters padraoMesAtual() {
    return TransactionsFilters(mesReferencia: mesReferenciaAtual());
  }
}

class TransactionsPageResult {
  TransactionsPageResult({
    required this.total,
    required this.pagina,
    required this.totalPaginas,
    required this.items,
  });

  final int total;
  final int pagina;
  final int totalPaginas;
  final List<TransacaoItem> items;
}

class TransactionsFilterOptions {
  TransactionsFilterOptions({
    required this.categorias,
    required this.contas,
    required this.tipos,
  });

  final List<String> categorias;
  final List<String> contas;
  final List<String> tipos;
}

class CadastroTransacaoOptions {
  CadastroTransacaoOptions({
    required this.categoriasDespesa,
    required this.categoriasReceita,
    required this.categoriasInvestimento,
    required this.contas,
    required this.contasInvestimento,
    required this.cartoesPagamento,
    required this.cartoesPagamentoTransferencia,
    required this.cartoesPagamentoDespesa,
  });

  final List<String> categoriasDespesa;
  final List<String> categoriasReceita;
  final List<String> categoriasInvestimento;
  final List<String> contas;
  final List<String> contasInvestimento;
  final List<String> cartoesPagamento;
  final List<String> cartoesPagamentoTransferencia;
  final List<String> cartoesPagamentoDespesa;
}

class CadastroTransacaoInput {
  CadastroTransacaoInput({
    required this.nome,
    required this.tipo,
    required this.valor,
    required this.categoria,
    required this.conta,
    required this.data,
    this.obs = '',
    this.tag,
    this.desconsiderar = false,
    this.parcelas,
  });

  final String nome;
  final String tipo;
  final double valor;
  final String categoria;
  final String conta;
  final DateTime data;
  final String obs;
  final String? tag;
  final bool desconsiderar;
  final int? parcelas;
}

class TransactionsRepository {
  TransactionsRepository(this._apiClient);

  final AlfredApiClient _apiClient;

  static const List<String> contasPadrao = [
    'Itaú CC',
    'Cartão Filippe',
    'Cartão Bianca',
    'Cartão Nath',
    'Inter',
    'Nubank',
    'VA',
    'VR',
  ];
  static const List<String> contasInvestimentoPadrao = ['Ion', 'Nuinvest', '99Pay', 'C6Invest'];
  static const List<String> cartoesPagamentoPadrao = [
    'Cartão Filippe',
    'Cartão Nath',
    'Cartão Bianca',
    'Cartão Pai',
    'Cartão Mãe',
  ];
  static const List<String> cartoesPagamentoTransferenciaPadrao = [
    'Cartão Nath',
    'Cartão Filippe',
    'Cartão Bianca',
  ];
  static const List<String> cartoesPagamentoDespesaPadrao = ['Cartão Pai', 'Cartão Mãe'];

  Future<TransactionsPageResult> listarPaginado({
    required int pagina,
    required int limite,
    required TransactionsFilters filtros,
  }) async {
    final intervaloMes = _intervaloMes(filtros.mesReferencia);
    final response = await _apiClient.getTransacoesPaginado(
      pagina: pagina,
      limite: limite,
      dataInicio: intervaloMes?.dataInicio,
      dataFim: intervaloMes?.dataFim,
      categoria: filtros.categoria,
      conta: filtros.conta,
      tipo: filtros.tipo,
    );

    return TransactionsPageResult(
      total: response.total,
      pagina: response.pagina,
      totalPaginas: response.totalPaginas,
      items: response.items.map(_mapDtoToItem).toList(),
    );
  }

  Future<TransactionsFilterOptions> carregarOpcoesFiltros() async {
    final CategoriasDto categoriasDto = await _apiClient.getCategorias();
    final transacoes = await _apiClient.getTransacoesPaginado(pagina: 1, limite: 200);

    final contas = transacoes.items
        .map((e) => e.conta)
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    final categorias = <String>{
      ...categoriasDto.despesa,
      ...categoriasDto.receita,
      ...categoriasDto.investimento,
    }.toList()
      ..sort();

    return TransactionsFilterOptions(
      categorias: categorias,
      contas: contas,
      tipos: const ['Despesa', 'Receita', 'Investimento', 'Transferencia', 'Transferência'],
    );
  }

  Future<CadastroTransacaoOptions> carregarOpcoesCadastro() async {
    final categoriasDto = await _apiClient.getCategorias();
    final saldo = await _apiClient.getSaldo();
    final contasSaldo = saldo.map((e) => e.conta).where((e) => e.isNotEmpty).toSet();
    final contas = contasPadrao.where((conta) => contasSaldo.contains(conta)).toList();
    final contasFinal = contas.isEmpty ? [...contasPadrao] : contas;

    return CadastroTransacaoOptions(
      categoriasDespesa: categoriasDto.despesa,
      categoriasReceita: categoriasDto.receita,
      categoriasInvestimento: categoriasDto.investimento,
      contas: contas,
      contasInvestimento: contasInvestimentoPadrao,
      cartoesPagamento: cartoesPagamentoPadrao,
      cartoesPagamentoTransferencia: cartoesPagamentoTransferenciaPadrao,
      cartoesPagamentoDespesa: cartoesPagamentoDespesaPadrao,
    );
  }

  Future<void> salvarFiltros(TransactionsFilters filtros) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_filtrosKey, jsonEncode(filtros.toMap()));
  }

  Future<TransactionsFilters> carregarFiltros() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString(_filtrosKey);
    if (json == null || json.isEmpty) {
      return TransactionsFilters.padraoMesAtual();
    }
    final map = jsonDecode(json) as Map<String, dynamic>;
    final filtros = TransactionsFilters.fromMap(map);
    if (filtros.mesReferencia == null || filtros.mesReferencia!.trim().isEmpty) {
      return filtros.copyWith(mesReferencia: TransactionsFilters.mesReferenciaAtual());
    }
    return filtros;
  }

  Future<void> cadastrarTransacao(CadastroTransacaoInput input) async {
    await _apiClient.postTransacao(
      CriarTransacaoRequestDto(
        nome: input.nome,
        tipo: input.tipo,
        valor: input.valor,
        categoria: input.categoria,
        conta: input.conta,
        dataIso: input.data.toIso8601String(),
        obs: input.obs,
        tag: input.tag,
        desconsiderar: input.desconsiderar,
        parcelas: input.parcelas,
      ),
    );
  }

  Future<void> editarTransacao(int id, CadastroTransacaoInput input) async {
    await _apiClient.putTransacao(
      id,
      CriarTransacaoRequestDto(
        nome: input.nome,
        tipo: input.tipo,
        valor: input.valor,
        categoria: input.categoria,
        conta: input.conta,
        dataIso: input.data.toIso8601String(),
        obs: input.obs,
        tag: input.tag,
        desconsiderar: input.desconsiderar,
        parcelas: input.parcelas,
      ),
    );
  }

  Future<void> excluirTransacao(int id) async {
    await _apiClient.deleteTransacao(id);
  }

  Future<void> atualizarFlagsTransacao(
    int id, {
    bool? desconsiderar,
    bool? grandeTransacao,
  }) async {
    await _apiClient.patchTransacaoFlags(
      id,
      desconsiderar: desconsiderar,
      grandeTransacao: grandeTransacao,
    );
  }

  TransacaoItem _mapDtoToItem(TransacaoDto item) {
    return TransacaoItem(
      id: item.id,
      nome: item.nome,
      tipo: item.tipo,
      valor: item.valor,
      categoria: item.categoria,
      conta: item.conta,
      data: item.data,
      obs: item.obs,
      tag: item.tag,
      desconsiderar: item.desconsiderar,
    );
  }

  _IntervaloMes? _intervaloMes(String? mesReferencia) {
    if (mesReferencia == null || mesReferencia.trim().isEmpty) {
      return null;
    }

    final partes = mesReferencia.trim().split('-');
    if (partes.length != 2) {
      return null;
    }

    final ano = int.tryParse(partes[0]);
    final mes = int.tryParse(partes[1]);
    if (ano == null || mes == null || mes < 1 || mes > 12) {
      return null;
    }

    final inicio = DateTime(ano, mes, 1);
    final fim = DateTime(ano, mes + 1, 0);
    return _IntervaloMes(
      dataInicio: _formatarDataFiltro(inicio),
      dataFim: _formatarDataFiltro(fim),
    );
  }

  String _formatarDataFiltro(DateTime data) {
    return '${data.year.toString().padLeft(4, '0')}-${data.month.toString().padLeft(2, '0')}-${data.day.toString().padLeft(2, '0')}';
  }
}

class _IntervaloMes {
  _IntervaloMes({
    required this.dataInicio,
    required this.dataFim,
  });

  final String dataInicio;
  final String dataFim;
}

class TransactionsState {
  TransactionsState({
    this.items = const [],
    this.filtros = const TransactionsFilters(),
    this.opcoes,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.hasMore = true,
    this.paginaAtual = 0,
    this.total = 0,
    this.errorMessage,
  });

  final List<TransacaoItem> items;
  final TransactionsFilters filtros;
  final TransactionsFilterOptions? opcoes;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final int paginaAtual;
  final int total;
  final String? errorMessage;

  TransactionsState copyWith({
    List<TransacaoItem>? items,
    TransactionsFilters? filtros,
    TransactionsFilterOptions? opcoes,
    bool? isLoading,
    bool? isLoadingMore,
    bool? hasMore,
    int? paginaAtual,
    int? total,
    String? errorMessage,
    bool clearError = false,
  }) {
    return TransactionsState(
      items: items ?? this.items,
      filtros: filtros ?? this.filtros,
      opcoes: opcoes ?? this.opcoes,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMore: hasMore ?? this.hasMore,
      paginaAtual: paginaAtual ?? this.paginaAtual,
      total: total ?? this.total,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

class TransactionsNotifier extends StateNotifier<TransactionsState> {
  TransactionsNotifier(this._repository) : super(TransactionsState());

  static const int _limite = 30;
  final TransactionsRepository _repository;
  CadastroTransacaoOptions? _opcoesCadastroCache;
  Future<CadastroTransacaoOptions>? _opcoesCadastroFuture;

  Future<void> inicializar() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      _precarregarOpcoesCadastro();
      final filtros = await _repository.carregarFiltros();
      final opcoes = await _repository.carregarOpcoesFiltros();
      state = state.copyWith(filtros: filtros, opcoes: opcoes);
      await recarregar();
    } catch (error) {
      state = state.copyWith(isLoading: false, errorMessage: error.toString());
    }
  }

  Future<void> recarregar() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final page = await _repository.listarPaginado(
        pagina: 1,
        limite: _limite,
        filtros: state.filtros,
      );
      state = state.copyWith(
        items: page.items,
        total: page.total,
        paginaAtual: 1,
        hasMore: page.pagina < page.totalPaginas,
        isLoading: false,
      );
    } catch (error) {
      state = state.copyWith(isLoading: false, errorMessage: error.toString());
    }
  }

  Future<void> carregarMais() async {
    if (state.isLoadingMore || state.isLoading || !state.hasMore) {
      return;
    }
    state = state.copyWith(isLoadingMore: true, clearError: true);
    try {
      final proximaPagina = state.paginaAtual + 1;
      final page = await _repository.listarPaginado(
        pagina: proximaPagina,
        limite: _limite,
        filtros: state.filtros,
      );
      state = state.copyWith(
        items: [...state.items, ...page.items],
        total: page.total,
        paginaAtual: page.pagina,
        hasMore: page.pagina < page.totalPaginas,
        isLoadingMore: false,
      );
    } catch (error) {
      state = state.copyWith(isLoadingMore: false, errorMessage: error.toString());
    }
  }

  Future<void> atualizarFiltros(TransactionsFilters filtros) async {
    await _repository.salvarFiltros(filtros);
    state = state.copyWith(filtros: filtros);
    await recarregar();
  }

  Future<CadastroTransacaoOptions> carregarOpcoesCadastro() {
    if (_opcoesCadastroCache != null) {
      return Future.value(_opcoesCadastroCache);
    }
    _opcoesCadastroFuture ??= _repository.carregarOpcoesCadastro().then((opcoes) {
      _opcoesCadastroCache = opcoes;
      return opcoes;
    }).whenComplete(() {
      _opcoesCadastroFuture = null;
    });
    return _opcoesCadastroFuture!;
  }

  Future<void> cadastrarTransacao(CadastroTransacaoInput input) async {
    await _repository.cadastrarTransacao(input);
    _precarregarOpcoesCadastro(forcar: true);
    await recarregar();
  }

  Future<void> editarTransacao(int id, CadastroTransacaoInput input) async {
    await _repository.editarTransacao(id, input);
    await recarregar();
  }

  Future<void> excluirTransacao(int id) async {
    await _repository.excluirTransacao(id);
    await recarregar();
  }

  Future<void> atualizarFlagsTransacao(
    int id, {
    bool? desconsiderar,
    bool? grandeTransacao,
  }) async {
    await _repository.atualizarFlagsTransacao(
      id,
      desconsiderar: desconsiderar,
      grandeTransacao: grandeTransacao,
    );
    await recarregar();
  }

  void _precarregarOpcoesCadastro({bool forcar = false}) {
    if (!forcar && (_opcoesCadastroCache != null || _opcoesCadastroFuture != null)) {
      return;
    }
    _opcoesCadastroFuture = _repository.carregarOpcoesCadastro().then((opcoes) {
      _opcoesCadastroCache = opcoes;
      return opcoes;
    }).whenComplete(() {
      _opcoesCadastroFuture = null;
    });
  }
}

final transactionsNotifierProvider =
    StateNotifierProvider<TransactionsNotifier, TransactionsState>((ref) {
  return TransactionsNotifier(ref.watch(transactionsRepositoryProvider));
});



