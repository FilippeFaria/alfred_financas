class SmsBankCatalogItemDto {
  SmsBankCatalogItemDto({
    required this.id,
    required this.nome,
  });

  factory SmsBankCatalogItemDto.fromJson(Map<String, dynamic> json) {
    return SmsBankCatalogItemDto(
      id: (json['id'] ?? '').toString(),
      nome: (json['nome'] ?? '').toString(),
    );
  }

  final String id;
  final String nome;
}

class SmsCapturePreferencesDto {
  SmsCapturePreferencesDto({
    required this.smsEnabled,
    required this.bancosSelecionados,
    required this.mapeamentoCartaoUltimos4,
    required this.catalogoBancos,
    required this.catalogoCartoes,
  });

  factory SmsCapturePreferencesDto.fromJson(Map<String, dynamic> json) {
    return SmsCapturePreferencesDto(
      smsEnabled: json['sms_enabled'] == true,
      bancosSelecionados: (json['bancos_selecionados'] as List<dynamic>? ?? [])
          .map((item) => item.toString())
          .toList(),
      mapeamentoCartaoUltimos4: (json['mapeamento_cartao_ultimos4'] as Map?)
              ?.map((key, value) => MapEntry(key.toString(), value.toString())) ??
          <String, String>{},
      catalogoBancos: (json['catalogo_bancos'] as List<dynamic>? ?? [])
          .map((item) => SmsBankCatalogItemDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      catalogoCartoes: (json['catalogo_cartoes'] as List<dynamic>? ?? [])
          .map((item) => item.toString())
          .toList(),
    );
  }

  final bool smsEnabled;
  final List<String> bancosSelecionados;
  final Map<String, String> mapeamentoCartaoUltimos4;
  final List<SmsBankCatalogItemDto> catalogoBancos;
  final List<String> catalogoCartoes;
}

class SmsCapturePreferencesUpdateDto {
  SmsCapturePreferencesUpdateDto({
    required this.smsEnabled,
    required this.bancosSelecionados,
    required this.mapeamentoCartaoUltimos4,
  });

  final bool smsEnabled;
  final List<String> bancosSelecionados;
  final Map<String, String> mapeamentoCartaoUltimos4;

  Map<String, dynamic> toJson() {
    return {
      'sms_enabled': smsEnabled,
      'bancos_selecionados': bancosSelecionados,
      'mapeamento_cartao_ultimos4': mapeamentoCartaoUltimos4,
    };
  }
}
