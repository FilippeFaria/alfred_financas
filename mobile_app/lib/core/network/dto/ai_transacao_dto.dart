class TransacaoSugeridaDto {
  TransacaoSugeridaDto({
    required this.data,
    required this.tipo,
    required this.categoria,
    required this.conta,
    required this.contaDestino,
    required this.nome,
    required this.valor,
    required this.origem,
    required this.descricaoOriginal,
    required this.transcricao,
    required this.confianca,
    required this.camposIncertos,
    required this.justificativa,
  });

  factory TransacaoSugeridaDto.fromJson(Map<String, dynamic> json) {
    return TransacaoSugeridaDto(
      data: json['data']?.toString(),
      tipo: json['tipo']?.toString(),
      categoria: json['categoria']?.toString(),
      conta: json['conta']?.toString(),
      contaDestino: json['conta_destino']?.toString(),
      nome: json['nome']?.toString(),
      valor: (json['valor'] as num?)?.toDouble(),
      origem: (json['origem'] ?? '').toString(),
      descricaoOriginal: (json['descricao_original'] ?? '').toString(),
      transcricao: json['transcricao']?.toString(),
      confianca: ((json['confianca'] as num?) ?? 0).toDouble(),
      camposIncertos: (json['campos_incertos'] as List<dynamic>? ?? [])
          .map((item) => item.toString())
          .toList(),
      justificativa: json['justificativa']?.toString(),
    );
  }

  final String? data;
  final String? tipo;
  final String? categoria;
  final String? conta;
  final String? contaDestino;
  final String? nome;
  final double? valor;
  final String origem;
  final String descricaoOriginal;
  final String? transcricao;
  final double confianca;
  final List<String> camposIncertos;
  final String? justificativa;
}

class TextoParaTransacaoResponseDto {
  TextoParaTransacaoResponseDto({
    required this.pendingTransactionId,
    required this.transacaoSugerida,
  });

  factory TextoParaTransacaoResponseDto.fromJson(Map<String, dynamic> json) {
    return TextoParaTransacaoResponseDto(
      pendingTransactionId: (json['pending_transaction_id'] ?? '').toString(),
      transacaoSugerida: TransacaoSugeridaDto.fromJson(
        Map<String, dynamic>.from(json['transacao_sugerida'] as Map),
      ),
    );
  }

  final String pendingTransactionId;
  final TransacaoSugeridaDto transacaoSugerida;
}

class AudioParaTransacaoResponseDto {
  AudioParaTransacaoResponseDto({
    required this.pendingTransactionId,
    required this.transcricao,
    required this.transacaoSugerida,
  });

  factory AudioParaTransacaoResponseDto.fromJson(Map<String, dynamic> json) {
    return AudioParaTransacaoResponseDto(
      pendingTransactionId: (json['pending_transaction_id'] ?? '').toString(),
      transcricao: (json['transcricao'] ?? '').toString(),
      transacaoSugerida: TransacaoSugeridaDto.fromJson(
        Map<String, dynamic>.from(json['transacao_sugerida'] as Map),
      ),
    );
  }

  final String pendingTransactionId;
  final String transcricao;
  final TransacaoSugeridaDto transacaoSugerida;
}
