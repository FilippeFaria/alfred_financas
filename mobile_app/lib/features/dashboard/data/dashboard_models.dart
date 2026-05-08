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

class AnaliseMetricas {
  AnaliseMetricas({
    required this.gastoAtual,
    required this.gastoAnterior,
    required this.gasto3mMedia,
    required this.deltaAnterior,
    required this.deltaAtual,
    required this.delta3m,
    required this.labelPrev,
    required this.labelCurr,
    required this.label3m,
  });

  final double gastoAtual;
  final double gastoAnterior;
  final double gasto3mMedia;
  final double? deltaAnterior;
  final double? deltaAtual;
  final double? delta3m;
  final String labelPrev;
  final String labelCurr;
  final String label3m;
}

class DashboardFilters {
  const DashboardFilters({
    this.anomeReferencia,
    this.desconsiderar = true,
    this.va = false,
    this.vr = false,
    this.bianca = false,
    this.filippe = false,
    this.dayToDate = true,
  });

  final int? anomeReferencia;
  final bool desconsiderar;
  final bool va;
  final bool vr;
  final bool bianca;
  final bool filippe;
  final bool dayToDate;

  DashboardFilters copyWith({
    int? anomeReferencia,
    bool? desconsiderar,
    bool? va,
    bool? vr,
    bool? bianca,
    bool? filippe,
    bool? dayToDate,
    bool clearAnomeReferencia = false,
  }) {
    return DashboardFilters(
      anomeReferencia: clearAnomeReferencia ? null : (anomeReferencia ?? this.anomeReferencia),
      desconsiderar: desconsiderar ?? this.desconsiderar,
      va: va ?? this.va,
      vr: vr ?? this.vr,
      bianca: bianca ?? this.bianca,
      filippe: filippe ?? this.filippe,
      dayToDate: dayToDate ?? this.dayToDate,
    );
  }
}

class DashboardSnapshot {
  DashboardSnapshot({
    required this.status,
    required this.metricas,
    required this.anomeReferencia,
    required this.anomesDisponiveis,
    required this.saldoTotal,
    required this.gastoMes,
    required this.orcamentoUsadoPercentual,
    required this.orcamentoUsadoLabel,
    required this.categoriasDestaque,
    required this.ultimosLancamentos,
    required this.saldos,
    required this.serieMensal,
    required this.serieCategoria,
  });

  final String status;
  final AnaliseMetricas metricas;
  final int anomeReferencia;
  final List<int> anomesDisponiveis;
  final double saldoTotal;
  final double gastoMes;
  final double orcamentoUsadoPercentual;
  final String orcamentoUsadoLabel;
  final List<CategoriaDestaque> categoriasDestaque;
  final List<LancamentoResumo> ultimosLancamentos;
  final List<SaldoConta> saldos;
  final List<SerieMensalResumo> serieMensal;
  final List<SerieMensalResumo> serieCategoria;
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

class SerieMensalResumo {
  SerieMensalResumo({
    required this.anome,
    required this.valor,
  });

  final int anome;
  final double valor;
}
