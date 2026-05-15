class TransacaoItem {
  TransacaoItem({
    required this.id,
    this.rowId,
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
  final String? rowId;
  final String nome;
  final String tipo;
  final double valor;
  final String categoria;
  final String conta;
  final String data;
  final String obs;
  final String? tag;
  final bool desconsiderar;

  factory TransacaoItem.fromJson(Map<String, dynamic> json) {
    return TransacaoItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      rowId: json['row_id']?.toString(),
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
