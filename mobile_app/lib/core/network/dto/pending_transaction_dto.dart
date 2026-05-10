import 'ai_transacao_dto.dart';

class PendingTransactionDto {
  PendingTransactionDto({
    required this.id,
    required this.userId,
    required this.source,
    required this.rawText,
    required this.transcription,
    required this.suggestedPayload,
    required this.confidence,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.transacaoSugerida,
  });

  factory PendingTransactionDto.fromJson(Map<String, dynamic> json) {
    final suggestedPayload = json['suggested_payload'] is Map
        ? Map<String, dynamic>.from(json['suggested_payload'] as Map)
        : <String, dynamic>{};
    final transacaoSugerida = suggestedPayload.isEmpty ? null : TransacaoSugeridaDto.fromJson(suggestedPayload);

    return PendingTransactionDto(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      source: (json['source'] ?? '').toString(),
      rawText: (json['raw_text'] ?? '').toString(),
      transcription: json['transcription']?.toString(),
      suggestedPayload: suggestedPayload,
      confidence: ((json['confidence'] as num?) ?? 0).toDouble(),
      status: (json['status'] ?? '').toString(),
      createdAt: DateTime.tryParse((json['created_at'] ?? '').toString()),
      updatedAt: DateTime.tryParse((json['updated_at'] ?? '').toString()),
      transacaoSugerida: transacaoSugerida,
    );
  }

  final String id;
  final String userId;
  final String source;
  final String rawText;
  final String? transcription;
  final Map<String, dynamic> suggestedPayload;
  final double confidence;
  final String status;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final TransacaoSugeridaDto? transacaoSugerida;
}

