class NotificacaoTransacaoResponseDto {
  NotificacaoTransacaoResponseDto({
    required this.created,
    required this.duplicate,
    required this.pendingTransactionId,
    required this.confidence,
    required this.message,
  });

  factory NotificacaoTransacaoResponseDto.fromJson(Map<String, dynamic> json) {
    return NotificacaoTransacaoResponseDto(
      created: json['created'] == true,
      duplicate: json['duplicate'] == true,
      pendingTransactionId: json['pending_transaction_id']?.toString(),
      confidence: (json['confidence'] as num?)?.toDouble(),
      message: (json['message'] ?? '').toString(),
    );
  }

  final bool created;
  final bool duplicate;
  final String? pendingTransactionId;
  final double? confidence;
  final String message;
}

