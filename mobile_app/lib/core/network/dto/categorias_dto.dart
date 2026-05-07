class CategoriasDto {
  CategoriasDto({
    required this.despesa,
    required this.receita,
    required this.investimento,
  });

  final List<String> despesa;
  final List<String> receita;
  final List<String> investimento;

  factory CategoriasDto.fromJson(Map<String, dynamic> json) {
    List<String> parseList(String key) {
      final raw = json[key] as List? ?? <dynamic>[];
      return raw.map((item) => item.toString()).toList();
    }

    return CategoriasDto(
      despesa: parseList('despesa'),
      receita: parseList('receita'),
      investimento: parseList('investimento'),
    );
  }
}
