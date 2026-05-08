import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/analise_resumo_dto.dart';
import '../../../core/network/dto/saldo_dto.dart';
import '../../../core/network/dto/status_dto.dart';
import '../../../core/network/dto/transacao_dto.dart';
import '../../../core/utils/formatters.dart';
import 'dashboard_models.dart';

final dashboardFiltersProvider =
    StateNotifierProvider<DashboardFiltersNotifier, DashboardFilters>((ref) {
  return DashboardFiltersNotifier();
});

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepository(ref.watch(alfredApiClientProvider));
});

class DashboardFiltersNotifier extends StateNotifier<DashboardFilters> {
  DashboardFiltersNotifier() : super(DashboardFilters(anomeReferencia: _anomeAtual()));

  void aplicar(DashboardFilters filtros) {
    state = filtros;
  }

  void atualizar({
    int? anomeReferencia,
    bool? desconsiderar,
    bool? va,
    bool? vr,
    bool? bianca,
    bool? filippe,
    bool? dayToDate,
    bool clearAnomeReferencia = false,
  }) {
    state = state.copyWith(
      anomeReferencia: anomeReferencia,
      desconsiderar: desconsiderar,
      va: va,
      vr: vr,
      bianca: bianca,
      filippe: filippe,
      dayToDate: dayToDate,
      clearAnomeReferencia: clearAnomeReferencia,
    );
  }

  void limpar() {
    state = DashboardFilters(anomeReferencia: _anomeAtual());
  }

  static int _anomeAtual() {
    final now = DateTime.now();
    return now.year * 100 + now.month;
  }
}

class DashboardRepository {
  DashboardRepository(this._apiClient);

  final AlfredApiClient _apiClient;
  final Map<String, DashboardSnapshot> _cache = {};

  String _cacheKey(DashboardFilters filtros) {
    return [
      filtros.anomeReferencia?.toString() ?? 'latest',
      filtros.desconsiderar,
      filtros.va,
      filtros.vr,
      filtros.bianca,
      filtros.filippe,
      filtros.dayToDate,
    ].join('|');
  }

  DashboardSnapshot? getCache(DashboardFilters filtros) {
    return _cache[_cacheKey(filtros)];
  }

  Future<DashboardSnapshot> carregarResumo({
    required DashboardFilters filtros,
    bool forceRefresh = false,
  }) async {
    final key = _cacheKey(filtros);
    if (!forceRefresh && _cache.containsKey(key)) {
      return _cache[key]!;
    }

    final StatusDto statusDto = await _apiClient.getHealth();
    final List<SaldoDto> saldosDto = await _apiClient.getSaldo();
    final AnaliseResumoDto analiseDto = await _apiClient.postAnaliseResumo(
      AnaliseResumoRequestDto(
        desconsiderar: filtros.desconsiderar,
        va: filtros.va,
        vr: filtros.vr,
        bianca: filtros.bianca,
        filippe: filtros.filippe,
        dayToDate: filtros.dayToDate,
        anomeReferencia: filtros.anomeReferencia,
      ),
    );

    final saldoJson = saldosDto
        .map((item) => SaldoConta(conta: item.conta, saldo: item.saldo))
        .toList()
      ..sort((a, b) => a.conta.compareTo(b.conta));
    final saldoTotal = saldoJson.fold<double>(0, (sum, item) => sum + item.saldo);

    final gastoMes = analiseDto.metricas.gastoAtual;
    final referenciaOrcamento = analiseDto.metricas.gasto3mMedia <= 0
        ? 1
        : analiseDto.metricas.gasto3mMedia;
    final orcamentoUsadoPercentual = (gastoMes / referenciaOrcamento) * 100;

    final categoriasDestaque = _agruparCategorias(analiseDto.items);
    final ultimosLancamentos = _ultimosLancamentos(analiseDto.items);

    final snapshot = DashboardSnapshot(
      status: statusDto.status,
      metricas: AnaliseMetricas(
        gastoAtual: analiseDto.metricas.gastoAtual,
        gastoAnterior: analiseDto.metricas.gastoAnterior,
        gasto3mMedia: analiseDto.metricas.gasto3mMedia,
        deltaAnterior: analiseDto.metricas.deltaAnterior,
        deltaAtual: analiseDto.metricas.deltaAtual,
        delta3m: analiseDto.metricas.delta3m,
        labelPrev: analiseDto.metricas.labelPrev,
        labelCurr: analiseDto.metricas.labelCurr,
        label3m: analiseDto.metricas.label3m,
      ),
      anomeReferencia: analiseDto.anomeReferencia,
      anomesDisponiveis: analiseDto.anomesDisponiveis,
      saldoTotal: saldoTotal,
      gastoMes: gastoMes,
      orcamentoUsadoPercentual: orcamentoUsadoPercentual,
      orcamentoUsadoLabel: 'Base media 3 meses: R\$ ${referenciaOrcamento.toStringAsFixed(2)}',
      categoriasDestaque: categoriasDestaque,
      ultimosLancamentos: ultimosLancamentos,
      saldos: saldoJson,
      items: analiseDto.items,
    );

    _cache[key] = snapshot;
    return snapshot;
  }

  List<CategoriaDestaque> _agruparCategorias(List<TransacaoDto> items) {
    final mapa = <String, double>{};
    for (final item in items) {
      if (item.tipo != 'Despesa') {
        continue;
      }
      final chave = item.categoria.trim().isEmpty ? 'Sem categoria' : item.categoria;
      mapa[chave] = (mapa[chave] ?? 0) + item.valor.abs();
    }

    final categorias = mapa.entries
        .map((entry) => CategoriaDestaque(nome: entry.key, valor: entry.value))
        .toList()
      ..sort((a, b) => b.valor.compareTo(a.valor));

    return categorias.take(6).toList();
  }

  List<LancamentoResumo> _ultimosLancamentos(List<TransacaoDto> items) {
    final ordenados = [...items]
      ..sort((a, b) {
        final dataA = tentarConverterParaData(a.data) ?? DateTime.fromMillisecondsSinceEpoch(0);
        final dataB = tentarConverterParaData(b.data) ?? DateTime.fromMillisecondsSinceEpoch(0);
        return dataB.compareTo(dataA);
      });
    return ordenados
        .take(5)
        .map(
          (item) => LancamentoResumo(
            nome: item.nome,
            categoria: item.categoria,
            valor: item.valor,
            data: item.data,
          ),
        )
        .toList();
  }
}

final dashboardSnapshotProvider = FutureProvider<DashboardSnapshot>((ref) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  final filtros = ref.watch(dashboardFiltersProvider);
  return repository.carregarResumo(filtros: filtros);
});
