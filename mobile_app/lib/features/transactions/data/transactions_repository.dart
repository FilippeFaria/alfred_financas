import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/alfred_api_client.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/dto/transacao_dto.dart';
import 'transaction_models.dart';

final transactionsRepositoryProvider = Provider<TransactionsRepository>((ref) {
  return TransactionsRepository(ref.watch(alfredApiClientProvider));
});

class TransactionsRepository {
  TransactionsRepository(this._apiClient);

  final AlfredApiClient _apiClient;

  Future<List<TransacaoItem>> listar({int limite = 30}) async {
    final response = await _apiClient.getTransacoes(limite: limite);
    final items = response.items
        .map(
          (TransacaoDto item) => TransacaoItem(
            id: item.id,
            nome: item.nome,
            tipo: item.tipo,
            valor: item.valor,
            categoria: item.categoria,
            conta: item.conta,
            data: item.data,
          ),
        )
        .toList();
    return items;
  }
}

final transactionsProvider = FutureProvider<List<TransacaoItem>>((ref) async {
  final repository = ref.watch(transactionsRepositoryProvider);
  return repository.listar();
});
