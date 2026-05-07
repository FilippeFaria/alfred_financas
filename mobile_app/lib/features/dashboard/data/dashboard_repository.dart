import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/analise_resumo_dto.dart';
import '../../../core/network/dto/saldo_dto.dart';
import '../../../core/network/dto/status_dto.dart';
import '../../../core/network/dto/transacao_dto.dart';
import 'dashboard_models.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepository(ref.watch(alfredApiClientProvider));
});

class DashboardRepository {
  DashboardRepository(this._apiClient);

  final AlfredApiClient _apiClient;
  DashboardSnapshot? _cache;

  DashboardSnapshot? get cache => _cache;

  Future<DashboardSnapshot> carregarResumo({bool forceRefresh = false}) async {
    if (!forceRefresh && _cache != null) {
      return _cache!;
    }

    final StatusDto statusDto = await _apiClient.getHealth();
    final List<SaldoDto> saldosDto = await _apiClient.getSaldo();
    final AnaliseResumoDto analiseDto = await _apiClient.postAnaliseResumo(
      AnaliseResumoRequestDto(dayToDate: true),
    );

    final saldoJson = saldosDto
        .map((item) => SaldoConta(conta: item.conta, saldo: item.saldo))
        .toList();
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
      saldoTotal: saldoTotal,
      gastoMes: gastoMes,
      orcamentoUsadoPercentual: orcamentoUsadoPercentual,
      orcamentoUsadoLabel:
          'Base media 3 meses: R\$ ${referenciaOrcamento.toStringAsFixed(2)}',
      categoriasDestaque: categoriasDestaque,
      ultimosLancamentos: ultimosLancamentos,
      saldos: saldoJson,
    );

    _cache = snapshot;
    return snapshot;
  }

  List<CategoriaDestaque> _agruparCategorias(List<TransacaoDto> items) {
    final mapa = <String, double>{};
    for (final item in items) {
      final chave = item.categoria.trim().isEmpty ? 'Sem categoria' : item.categoria;
      mapa[chave] = (mapa[chave] ?? 0) + item.valor.abs();
    }

    final categorias = mapa.entries
        .map((entry) => CategoriaDestaque(nome: entry.key, valor: entry.value))
        .toList()
      ..sort((a, b) => b.valor.compareTo(a.valor));

    return categorias.take(3).toList();
  }

  List<LancamentoResumo> _ultimosLancamentos(List<TransacaoDto> items) {
    final ordenados = [...items]..sort((a, b) => b.data.compareTo(a.data));
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
  return repository.carregarResumo();
});
