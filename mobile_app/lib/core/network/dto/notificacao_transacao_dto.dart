import 'ai_transacao_dto.dart';

class NotificacaoTransacaoResponseDto {
  NotificacaoTransacaoResponseDto({
    required this.created,
    required this.duplicate,
    required this.pendingTransactionId,
    required this.confidence,
    required this.duplicateReason,
    required this.transacaoSugerida,
    required this.message,
  });

  factory NotificacaoTransacaoResponseDto.fromJson(Map<String, dynamic> json) {
    final transacaoSugerida = json['transacao_sugerida'] is Map
        ? TransacaoSugeridaDto.fromJson(Map<String, dynamic>.from(json['transacao_sugerida'] as Map))
        : null;
    return NotificacaoTransacaoResponseDto(
      created: json['created'] == true,
      duplicate: json['duplicate'] == true,
      pendingTransactionId: json['pending_transaction_id']?.toString(),
      confidence: (json['confidence'] as num?)?.toDouble(),
      duplicateReason: json['duplicate_reason']?.toString(),
      transacaoSugerida: transacaoSugerida,
      message: (json['message'] ?? '').toString(),
    );
  }

  final bool created;
  final bool duplicate;
  final String? pendingTransactionId;
  final double? confidence;
  final String? duplicateReason;
  final TransacaoSugeridaDto? transacaoSugerida;
  final String message;
}
