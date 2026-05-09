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
    this.tag,
    this.desconsiderar = false,
  });

  final int id;
  final String nome;
  final String tipo;
  final double valor;
  final String categoria;
  final String conta;
  final String data;
  final String obs;
  final String? tag;
  final bool desconsiderar;

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
      tag: json['tag']?.toString(),
      desconsiderar: json['desconsiderar'] == true,
    );
  }
}

class TransacoesResponseDto {
  TransacoesResponseDto({
    required this.total,
    required this.pagina,
    required this.limite,
    required this.totalPaginas,
    required this.items,
  });

  final int total;
  final int pagina;
  final int limite;
  final int totalPaginas;
  final List<TransacaoDto> items;

  factory TransacoesResponseDto.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List? ?? <dynamic>[];
    return TransacoesResponseDto(
      total: (json['total'] as num?)?.toInt() ?? rawItems.length,
      pagina: (json['pagina'] as num?)?.toInt() ?? 1,
      limite: (json['limite'] as num?)?.toInt() ?? rawItems.length,
      totalPaginas: (json['total_paginas'] as num?)?.toInt() ?? 1,
      items: rawItems
          .map((item) => TransacaoDto.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }
}
