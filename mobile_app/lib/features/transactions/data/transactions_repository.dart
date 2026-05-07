import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/categorias_dto.dart';
import '../../../core/network/dto/transacao_dto.dart';
import 'transaction_models.dart';

const _filtrosKey = 'transactions_filters_v1';

final transactionsRepositoryProvider = Provider<TransactionsRepository>((ref) {
  return TransactionsRepository(ref.watch(alfredApiClientProvider));
});

class TransactionsFilters {
  const TransactionsFilters({
    this.dataInicio,
    this.dataFim,
    this.categoria,
    this.conta,
    this.tipo,
  });

  final String? dataInicio;
  final String? dataFim;
  final String? categoria;
  final String? conta;
  final String? tipo;

  TransactionsFilters copyWith({
    String? dataInicio,
    String? dataFim,
    String? categoria,
    String? conta,
    String? tipo,
    bool clearDataInicio = false,
    bool clearDataFim = false,
    bool clearCategoria = false,
    bool clearConta = false,
    bool clearTipo = false,
  }) {
    return TransactionsFilters(
      dataInicio: clearDataInicio ? null : (dataInicio ?? this.dataInicio),
      dataFim: clearDataFim ? null : (dataFim ?? this.dataFim),
      categoria: clearCategoria ? null : (categoria ?? this.categoria),
      conta: clearConta ? null : (conta ?? this.conta),
      tipo: clearTipo ? null : (tipo ?? this.tipo),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'data_inicio': dataInicio,
      'data_fim': dataFim,
      'categoria': categoria,
      'conta': conta,
      'tipo': tipo,
    };
  }

  factory TransactionsFilters.fromMap(Map<String, dynamic> map) {
    return TransactionsFilters(
      dataInicio: map['data_inicio']?.toString(),
      dataFim: map['data_fim']?.toString(),
      categoria: map['categoria']?.toString(),
      conta: map['conta']?.toString(),
      tipo: map['tipo']?.toString(),
    );
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

class TransactionsRepository {
  TransactionsRepository(this._apiClient);

  final AlfredApiClient _apiClient;

  Future<TransactionsPageResult> listarPaginado({
    required int pagina,
    required int limite,
    required TransactionsFilters filtros,
  }) async {
    final response = await _apiClient.getTransacoesPaginado(
      pagina: pagina,
      limite: limite,
      dataInicio: filtros.dataInicio,
      dataFim: filtros.dataFim,
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

    final contas = transacoes.items.map((e) => e.conta).where((e) => e.isNotEmpty).toSet().toList()..sort();
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

  Future<void> salvarFiltros(TransactionsFilters filtros) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_filtrosKey, jsonEncode(filtros.toMap()));
  }

  Future<TransactionsFilters> carregarFiltros() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString(_filtrosKey);
    if (json == null || json.isEmpty) {
      return TransactionsFilters();
    }
    final map = jsonDecode(json) as Map<String, dynamic>;
    return TransactionsFilters.fromMap(map);
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
    );
  }
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

  Future<void> inicializar() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
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
}

final transactionsNotifierProvider =
    StateNotifierProvider<TransactionsNotifier, TransactionsState>((ref) {
  return TransactionsNotifier(ref.watch(transactionsRepositoryProvider));
});
