class TransacaoItem {
  TransacaoItem({
    required this.id,
    required this.nome,
    required this.tipo,
    required this.valor,
    required this.categoria,
    required this.conta,
    required this.data,
  });

  final int id;
  final String nome;
  final String tipo;
  final double valor;
  final String categoria;
  final String conta;
  final String data;

  factory TransacaoItem.fromJson(Map<String, dynamic> json) {
    return TransacaoItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      nome: (json['nome'] ?? '').toString(),
      tipo: (json['tipo'] ?? '').toString(),
      valor: (json['valor'] as num?)?.toDouble() ?? 0,
      categoria: (json['categoria'] ?? '').toString(),
      conta: (json['conta'] ?? '').toString(),
      data: (json['data'] ?? '').toString(),
    );
  }
}
