import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/ai_transacao_dto.dart';
import '../../../core/network/dto/analise_resumo_dto.dart';
import '../../../core/network/dto/categorias_dto.dart';
import '../../../core/network/dto/notificacao_transacao_dto.dart';
import '../../../core/network/dto/pending_transaction_dto.dart';
import '../../../core/network/dto/transacao_dto.dart';

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

  Future<TextoParaTransacaoResponseDto> interpretarTransacaoPorTexto(String texto) {
    return _apiClient.postAiTextoTransacao(texto);
  }

  Future<AudioParaTransacaoResponseDto> interpretarTransacaoPorAudio({
    String? filePath,
    List<int>? fileBytes,
    String? fileName,
  }) {
    return _apiClient.postAiAudioTransacao(
      filePath: filePath,
      fileBytes: fileBytes,
      fileName: fileName,
    );
  }

  Future<TransacaoDto> confirmarTransacaoPendente(
    String pendingId, {
    Map<String, dynamic>? payload,
  }) {
    return _apiClient.confirmarTransacaoPendente(
      pendingId,
      payload: payload,
    );
  }

  Future<void> ignorarTransacaoPendente(String pendingId) {
    return _apiClient.ignorarTransacaoPendente(pendingId);
  }

  Future<List<PendingTransactionDto>> carregarPendenciasNotificacao() async {
    final pendencias = await _apiClient.getPendenciasIa(status: 'pending');
    return pendencias.where((item) => item.source == 'android_notification').toList();
  }

  Future<NotificacaoTransacaoResponseDto> interpretarTransacaoPorNotificacao({
    required String packageName,
    required String appName,
    required String title,
    required String text,
    String? subText,
    required String postedAt,
    required String notificationKey,
  }) {
    return _apiClient.postAiNotificacaoTransacao(
      packageName: packageName,
      appName: appName,
      title: title,
      text: text,
      subText: subText,
      postedAt: postedAt,
      notificationKey: notificationKey,
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
