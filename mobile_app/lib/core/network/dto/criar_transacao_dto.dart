class CriarTransacaoRequestDto {
  CriarTransacaoRequestDto({
    required this.nome,
    required this.tipo,
    required this.valor,
    required this.categoria,
    required this.conta,
    required this.dataIso,
    this.obs = '',
    this.tag,
    this.desconsiderar = false,
    this.parcelas,
    this.ignorarDuplicata = false,
    this.contaDestino,
    this.linhaId,
    this.atualizarApenasLinha = false,
  });

  final String nome;
  final String tipo;
  final double valor;
  final String categoria;
  final String conta;
  final String dataIso;
  final String obs;
  final String? tag;
  final bool desconsiderar;
  final int? parcelas;
  final bool ignorarDuplicata;
  final String? contaDestino;
  final String? linhaId;
  final bool atualizarApenasLinha;

  Map<String, dynamic> toJson() {
    return {
      'nome': nome,
      'tipo': tipo,
      'valor': valor,
      'categoria': categoria,
      'conta': conta,
      'data': dataIso,
      'obs': obs,
      'tag': tag,
      'desconsiderar': desconsiderar,
      'parcelas': parcelas,
      'ignorar_duplicata': ignorarDuplicata,
      'conta_destino': contaDestino,
      'linha_id': linhaId,
      'atualizar_apenas_linha': atualizarApenasLinha,
    };
  }
}
