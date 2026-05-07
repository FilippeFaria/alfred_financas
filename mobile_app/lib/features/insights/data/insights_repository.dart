import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/analise_resumo_dto.dart';
import '../../../core/network/dto/categorias_dto.dart';

final insightsRepositoryProvider = Provider<InsightsRepository>((ref) {
  return InsightsRepository(ref.watch(alfredApiClientProvider));
});

class InsightsRepository {
  InsightsRepository(this._apiClient);

  final AlfredApiClient _apiClient;

  Future<CategoriasDto> carregarCategorias() {
    return _apiClient.getCategorias();
  }

  Future<AnaliseResumoDto> carregarResumoAnalise({
    int? anomeReferencia,
    bool dayToDate = true,
  }) {
    return _apiClient.postAnaliseResumo(
      AnaliseResumoRequestDto(
        anomeReferencia: anomeReferencia,
        dayToDate: dayToDate,
      ),
    );
  }
}

final categoriasProvider = FutureProvider<CategoriasDto>((ref) async {
  final repo = ref.watch(insightsRepositoryProvider);
  return repo.carregarCategorias();
});

final analiseResumoProvider = FutureProvider<AnaliseResumoDto>((ref) async {
  final repo = ref.watch(insightsRepositoryProvider);
  return repo.carregarResumoAnalise();
});
