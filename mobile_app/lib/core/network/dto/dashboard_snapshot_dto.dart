import 'analise_resumo_dto.dart';
import 'saldo_dto.dart';

class DashboardSerieMensalDto {
  DashboardSerieMensalDto({
    required this.anome,
    required this.valor,
  });

  final int anome;
  final double valor;

  factory DashboardSerieMensalDto.fromJson(Map<String, dynamic> json) {
    return DashboardSerieMensalDto(
      anome: (json['anome'] as num?)?.toInt() ?? 0,
      valor: (json['valor'] as num?)?.toDouble() ?? 0,
    );
  }
}

class DashboardCategoriaDestaqueDto {
  DashboardCategoriaDestaqueDto({
    required this.nome,
    required this.valor,
    this.percentualOrcamento,
  });

  final String nome;
  final double valor;
  final double? percentualOrcamento;

  factory DashboardCategoriaDestaqueDto.fromJson(Map<String, dynamic> json) {
    return DashboardCategoriaDestaqueDto(
      nome: (json['nome'] ?? '').toString(),
      valor: (json['valor'] as num?)?.toDouble() ?? 0,
      percentualOrcamento: (json['percentual_orcamento'] as num?)?.toDouble(),
    );
  }
}

class DashboardUltimoLancamentoDto {
  DashboardUltimoLancamentoDto({
    required this.nome,
    required this.categoria,
    required this.valor,
    required this.data,
  });

  final String nome;
  final String categoria;
  final double valor;
  final String data;

  factory DashboardUltimoLancamentoDto.fromJson(Map<String, dynamic> json) {
    return DashboardUltimoLancamentoDto(
      nome: (json['nome'] ?? '').toString(),
      categoria: (json['categoria'] ?? '').toString(),
      valor: (json['valor'] as num?)?.toDouble() ?? 0,
      data: (json['data'] ?? '').toString(),
    );
  }
}

class DashboardSnapshotDto {
  DashboardSnapshotDto({
    required this.status,
    required this.anomeReferencia,
    required this.anomesDisponiveis,
    required this.metricas,
    required this.saldoTotal,
    required this.saldos,
    required this.gastoMes,
    required this.orcamentoUsadoPercentual,
    required this.orcamentoUsadoLabel,
    required this.categoriasDestaque,
    required this.ultimosLancamentos,
    required this.serieMensal,
    required this.serieReceitasMensal,
    required this.serieCategoria,
  });

  final String status;
  final int anomeReferencia;
  final List<int> anomesDisponiveis;
  final AnaliseMetricasDto metricas;
  final double saldoTotal;
  final List<SaldoDto> saldos;
  final double gastoMes;
  final double orcamentoUsadoPercentual;
  final String orcamentoUsadoLabel;
  final List<DashboardCategoriaDestaqueDto> categoriasDestaque;
  final List<DashboardUltimoLancamentoDto> ultimosLancamentos;
  final List<DashboardSerieMensalDto> serieMensal;
  final List<DashboardSerieMensalDto> serieReceitasMensal;
  final List<DashboardSerieMensalDto> serieCategoria;

  factory DashboardSnapshotDto.fromJson(Map<String, dynamic> json) {
    return DashboardSnapshotDto(
      status: (json['status'] ?? '').toString(),
      anomeReferencia: (json['anome_referencia'] as num?)?.toInt() ?? 0,
      anomesDisponiveis: (json['anomes_disponiveis'] as List? ?? <dynamic>[])
          .map((item) => (item as num).toInt())
          .toList(),
      metricas: AnaliseMetricasDto.fromJson(
        Map<String, dynamic>.from(json['metricas'] as Map? ?? <String, dynamic>{}),
      ),
      saldoTotal: (json['saldo_total'] as num?)?.toDouble() ?? 0,
      saldos: (json['saldos'] as List? ?? <dynamic>[])
          .map((item) => SaldoDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      gastoMes: (json['gasto_mes'] as num?)?.toDouble() ?? 0,
      orcamentoUsadoPercentual: (json['orcamento_usado_percentual'] as num?)?.toDouble() ?? 0,
      orcamentoUsadoLabel: (json['orcamento_usado_label'] ?? '').toString(),
      categoriasDestaque: (json['categorias_destaque'] as List? ?? <dynamic>[])
          .map((item) => DashboardCategoriaDestaqueDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      ultimosLancamentos: (json['ultimos_lancamentos'] as List? ?? <dynamic>[])
          .map((item) => DashboardUltimoLancamentoDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      serieMensal: (json['serie_mensal'] as List? ?? <dynamic>[])
          .map((item) => DashboardSerieMensalDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      serieReceitasMensal: (json['serie_receitas_mensal'] as List? ?? <dynamic>[])
          .map((item) => DashboardSerieMensalDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      serieCategoria: (json['serie_categoria'] as List? ?? <dynamic>[])
          .map((item) => DashboardSerieMensalDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }
}
