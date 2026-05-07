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
    required this.saldoTotal,
    required this.gastoMes,
    required this.orcamentoUsadoPercentual,
    required this.orcamentoUsadoLabel,
    required this.categoriasDestaque,
    required this.ultimosLancamentos,
    required this.saldos,
  });

  final String status;
  final double saldoTotal;
  final double gastoMes;
  final double orcamentoUsadoPercentual;
  final String orcamentoUsadoLabel;
  final List<CategoriaDestaque> categoriasDestaque;
  final List<LancamentoResumo> ultimosLancamentos;
  final List<SaldoConta> saldos;
}

class CategoriaDestaque {
  CategoriaDestaque({
    required this.nome,
    required this.valor,
  });

  final String nome;
  final double valor;
}

class LancamentoResumo {
  LancamentoResumo({
    required this.nome,
    required this.categoria,
    required this.valor,
    required this.data,
  });

  final String nome;
  final String categoria;
  final double valor;
  final String data;
}
