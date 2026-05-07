class TransacaoDto {
  TransacaoDto({
    required this.id,
    required this.nome,
    required this.tipo,
    required this.valor,
    required this.categoria,
    required this.conta,
    required this.data,
    this.obs = '',
  });

  final int id;
  final String nome;
  final String tipo;
  final double valor;
  final String categoria;
  final String conta;
  final String data;
  final String obs;

  factory TransacaoDto.fromJson(Map<String, dynamic> json) {
    return TransacaoDto(
      id: (json['id'] as num?)?.toInt() ?? 0,
      nome: (json['nome'] ?? '').toString(),
      tipo: (json['tipo'] ?? '').toString(),
      valor: (json['valor'] as num?)?.toDouble() ?? 0,
      categoria: (json['categoria'] ?? '').toString(),
      conta: (json['conta'] ?? '').toString(),
      data: (json['data'] ?? '').toString(),
      obs: (json['obs'] ?? '').toString(),
    );
  }
}

class TransacoesResponseDto {
  TransacoesResponseDto({
    required this.total,
    required this.items,
  });

  final int total;
  final List<TransacaoDto> items;

  factory TransacoesResponseDto.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List? ?? <dynamic>[];
    return TransacoesResponseDto(
      total: (json['total'] as num?)?.toInt() ?? rawItems.length,
      items: rawItems
          .map((item) => TransacaoDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }
}
