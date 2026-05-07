class SaldoDto {
  SaldoDto({
    required this.conta,
    required this.saldo,
  });

  final String conta;
  final double saldo;

  factory SaldoDto.fromJson(Map<String, dynamic> json) {
    return SaldoDto(
      conta: (json['conta'] ?? '').toString(),
      saldo: (json['saldo'] as num?)?.toDouble() ?? 0,
    );
  }
}
