import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/dashboard_snapshot_dto.dart';
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

  String _cacheKey(DashboardFilters filtros, String? categoria, int mesesHistorico) {
    return [
      filtros.anomeReferencia?.toString() ?? 'latest',
      filtros.desconsiderar,
      filtros.va,
      filtros.vr,
      filtros.bianca,
      filtros.filippe,
      filtros.dayToDate,
      categoria?.trim().isEmpty == false ? categoria!.trim() : 'all',
      mesesHistorico.clamp(3, 12),
    ].join('|');
  }

  DashboardSnapshot? getCache(
    DashboardFilters filtros, {
    String? categoria,
    int mesesHistorico = 6,
  }) {
    return _cache[_cacheKey(filtros, categoria, mesesHistorico)];
  }

  Future<List<String>> carregarCategoriasDespesa() async {
    final categorias = await _apiClient.getCategorias();
    return categorias.despesa;
  }

  Future<Map<String, double>> carregarOrcamentoAtual() async {
    final payload = await _apiClient.getOrcamentoValores();
    final rawItems = (payload['items'] as List? ?? <dynamic>[]);
    final result = <String, double>{};
    for (final raw in rawItems) {
      final item = Map<String, dynamic>.from(raw as Map);
      final categoria = (item['categoria'] ?? '').toString().trim();
      if (categoria.isEmpty) {
        continue;
      }
      result[categoria] = (item['valor'] as num?)?.toDouble() ?? 0.0;
    }
    return result;
  }

  Future<void> salvarOrcamento(Map<String, double> valores) async {
    final items = valores.entries
        .map((entry) => <String, dynamic>{
              'categoria': entry.key,
              'valor': entry.value,
            })
        .toList();
    await _apiClient.postOrcamentoValores(items: items);
  }

  Future<DashboardSnapshot> carregarResumo({
    required DashboardFilters filtros,
    String? categoria,
    int mesesHistorico = 6,
    bool forceRefresh = false,
  }) async {
    final key = _cacheKey(filtros, categoria, mesesHistorico);
    if (!forceRefresh && _cache.containsKey(key)) {
      return _cache[key]!;
    }
    final stopwatch = Stopwatch()..start();

    final DashboardSnapshotDto dto = await _apiClient.getDashboardSnapshot(
      desconsiderar: filtros.desconsiderar,
      va: filtros.va,
      vr: filtros.vr,
      bianca: filtros.bianca,
      filippe: filtros.filippe,
      dayToDate: filtros.dayToDate,
      anomeReferencia: filtros.anomeReferencia,
      categoria: categoria,
      mesesHistorico: mesesHistorico,
    );

    final saldoJson = dto.saldos
        .map((item) => SaldoConta(conta: item.conta, saldo: item.saldo))
        .toList()
      ..sort((a, b) => a.conta.compareTo(b.conta));

    final snapshot = DashboardSnapshot(
      status: dto.status,
      metricas: AnaliseMetricas(
        gastoAtual: dto.metricas.gastoAtual,
        gastoAnterior: dto.metricas.gastoAnterior,
        gasto3mMedia: dto.metricas.gasto3mMedia,
        deltaAnterior: dto.metricas.deltaAnterior,
        deltaAtual: dto.metricas.deltaAtual,
        delta3m: dto.metricas.delta3m,
        labelPrev: dto.metricas.labelPrev,
        labelCurr: dto.metricas.labelCurr,
        label3m: dto.metricas.label3m,
      ),
      anomeReferencia: dto.anomeReferencia,
      anomesDisponiveis: dto.anomesDisponiveis,
      saldoTotal: dto.saldoTotal,
      gastoMes: dto.gastoMes,
      orcamentoUsadoPercentual: dto.orcamentoUsadoPercentual,
      orcamentoUsadoLabel: dto.orcamentoUsadoLabel,
      categoriasDestaque: dto.categoriasDestaque
          .map((item) => CategoriaDestaque(
                nome: item.nome,
                valor: item.valor,
                percentualOrcamento: item.percentualOrcamento,
              ))
          .toList(),
      ultimosLancamentos: dto.ultimosLancamentos
          .map((item) => LancamentoResumo(nome: item.nome, categoria: item.categoria, valor: item.valor, data: item.data))
          .toList(),
      saldos: saldoJson,
      serieMensal: dto.serieMensal.map((item) => SerieMensalResumo(anome: item.anome, valor: item.valor)).toList(),
      serieReceitasMensal: dto.serieReceitasMensal.map((item) => SerieMensalResumo(anome: item.anome, valor: item.valor)).toList(),
      serieCategoria: dto.serieCategoria.map((item) => SerieMensalResumo(anome: item.anome, valor: item.valor)).toList(),
    );

    _cache[key] = snapshot;
    stopwatch.stop();
    debugPrint('[dashboard] snapshot carregado em ${stopwatch.elapsedMilliseconds}ms (forceRefresh=$forceRefresh)');
    return snapshot;
  }
}

final dashboardSnapshotProvider = FutureProvider.family<DashboardSnapshot, ({DashboardFilters filtros, String? categoria, int mesesHistorico})>((ref, args) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  return repository.carregarResumo(
    filtros: args.filtros,
    categoria: args.categoria,
    mesesHistorico: args.mesesHistorico,
  );
});
