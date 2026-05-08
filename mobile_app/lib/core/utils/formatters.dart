String formatarMoeda(num valor) {
  final negativo = valor < 0;
  final absoluto = valor.abs().toStringAsFixed(2);
  final partes = absoluto.split('.');
  final parteInteira = _formatarParteInteira(partes[0]);
  final parteDecimal = partes.length > 1 ? partes[1] : '00';

  return 'R\$ ${negativo ? '-' : ''}$parteInteira,$parteDecimal';
}

String formatarPercentual(num valor) {
  return '${valor.toStringAsFixed(1).replaceAll('.', ',')}%';
}

String formatarDataCurta(String valorBruto) {
  final data = tentarConverterParaData(valorBruto);
  if (data == null) {
    return valorBruto;
  }

  final dia = data.day.toString().padLeft(2, '0');
  final mes = data.month.toString().padLeft(2, '0');
  final hora = data.hour.toString().padLeft(2, '0');
  final minuto = data.minute.toString().padLeft(2, '0');

  return '$dia/$mes/${data.year} $hora:$minuto';
}

DateTime? tentarConverterParaData(String valorBruto) {
  if (valorBruto.trim().isEmpty) {
    return null;
  }

  final parsedIso = DateTime.tryParse(valorBruto);
  if (parsedIso != null) {
    return parsedIso;
  }

  final padraoBr = RegExp(
    r'^(\d{2})/(\d{2})/(\d{4})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$',
  );
  final matchBr = padraoBr.firstMatch(valorBruto);
  if (matchBr != null) {
    final dia = int.tryParse(matchBr.group(1) ?? '');
    final mes = int.tryParse(matchBr.group(2) ?? '');
    final ano = int.tryParse(matchBr.group(3) ?? '');
    final hora = int.tryParse(matchBr.group(4) ?? '') ?? 0;
    final minuto = int.tryParse(matchBr.group(5) ?? '') ?? 0;
    final segundo = int.tryParse(matchBr.group(6) ?? '') ?? 0;

    if (dia != null && mes != null && ano != null) {
      return DateTime(ano, mes, dia, hora, minuto, segundo);
    }
  }

  return null;
}

String _formatarParteInteira(String valor) {
  if (valor.length <= 3) {
    return valor;
  }

  final buffer = StringBuffer();
  final primeiroGrupo = valor.length % 3;
  final inicioPrimeiroGrupo = primeiroGrupo == 0 ? 3 : primeiroGrupo;

  buffer.write(valor.substring(0, inicioPrimeiroGrupo));
  for (var i = inicioPrimeiroGrupo; i < valor.length; i += 3) {
    buffer.write('.');
    buffer.write(valor.substring(i, i + 3));
  }

  return buffer.toString();
}
