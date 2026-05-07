class ApiException implements Exception {
  ApiException({
    required this.message,
    this.statusCode,
    this.code,
    this.details,
  });

  final String message;
  final int? statusCode;
  final String? code;
  final Map<String, dynamic>? details;

  @override
  String toString() {
    final status = statusCode != null ? ' (HTTP $statusCode)' : '';
    return 'ApiException$status: $message';
  }
}
