import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/saldo_dto.dart';
import '../../../core/network/dto/status_dto.dart';
import 'dashboard_models.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepository(ref.watch(alfredApiClientProvider));
});

class DashboardRepository {
  DashboardRepository(this._apiClient);

  final AlfredApiClient _apiClient;

  Future<DashboardSnapshot> carregarResumo() async {
    final StatusDto statusDto = await _apiClient.getHealth();
    final List<SaldoDto> saldosDto = await _apiClient.getSaldo();

    final saldoJson = saldosDto
        .map((item) => SaldoConta(conta: item.conta, saldo: item.saldo))
        .toList();

    return DashboardSnapshot(
      status: statusDto.status,
      saldos: saldoJson,
    );
  }
}

final dashboardSnapshotProvider = FutureProvider<DashboardSnapshot>((ref) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  return repository.carregarResumo();
});
