class StatusResponse {
  StatusResponse({required this.status});

  final String status;

  factory StatusResponse.fromJson(Map<String, dynamic> json) {
    return StatusResponse(status: (json['status'] ?? '').toString());
  }
}

class SaldoConta {
  SaldoConta({
    required this.conta,
    required this.saldo,
  });

  final String conta;
  final double saldo;

  factory SaldoConta.fromJson(Map<String, dynamic> json) {
    return SaldoConta(
      conta: (json['conta'] ?? '').toString(),
      saldo: (json['saldo'] as num?)?.toDouble() ?? 0,
    );
  }
}

class DashboardSnapshot {
  DashboardSnapshot({
    required this.status,
    required this.saldos,
  });

  final String status;
  final List<SaldoConta> saldos;
}
