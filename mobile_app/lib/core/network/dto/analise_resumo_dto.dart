import 'transacao_dto.dart';

class AnaliseResumoRequestDto {
  AnaliseResumoRequestDto({
    this.desconsiderar = true,
    this.va = false,
    this.vr = false,
    this.bianca = false,
    this.filippe = false,
    this.dayToDate = false,
    this.anomeReferencia,
  });

  final bool desconsiderar;
  final bool va;
  final bool vr;
  final bool bianca;
  final bool filippe;
  final bool dayToDate;
  final int? anomeReferencia;

  Map<String, dynamic> toJson() {
    return {
      'desconsiderar': desconsiderar,
      'va': va,
      'vr': vr,
      'bianca': bianca,
      'filippe': filippe,
      'day_to_date': dayToDate,
      'anome_referencia': anomeReferencia,
    };
  }
}

class AnaliseMetricasDto {
  AnaliseMetricasDto({
    required this.gastoAtual,
    required this.gastoAnterior,
    required this.gasto3mMedia,
  });

  final double gastoAtual;
  final double gastoAnterior;
  final double gasto3mMedia;

  factory AnaliseMetricasDto.fromJson(Map<String, dynamic> json) {
    return AnaliseMetricasDto(
      gastoAtual: (json['gasto_atual'] as num?)?.toDouble() ?? 0,
      gastoAnterior: (json['gasto_anterior'] as num?)?.toDouble() ?? 0,
      gasto3mMedia: (json['gasto_3m_media'] as num?)?.toDouble() ?? 0,
    );
  }
}

class AnaliseResumoDto {
  AnaliseResumoDto({
    required this.anomeReferencia,
    required this.anomesDisponiveis,
    required this.metricas,
    required this.items,
  });

  final int anomeReferencia;
  final List<int> anomesDisponiveis;
  final AnaliseMetricasDto metricas;
  final List<TransacaoDto> items;

  factory AnaliseResumoDto.fromJson(Map<String, dynamic> json) {
    final anos = (json['anomes_disponiveis'] as List? ?? <dynamic>[])
        .map((item) => (item as num).toInt())
        .toList();

    return AnaliseResumoDto(
      anomeReferencia: (json['anome_referencia'] as num?)?.toInt() ?? 0,
      anomesDisponiveis: anos,
      metricas: AnaliseMetricasDto.fromJson(
        Map<String, dynamic>.from(json['metricas'] as Map? ?? <String, dynamic>{}),
      ),
      items: (json['items'] as List? ?? <dynamic>[])
          .map((item) => TransacaoDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }
}
