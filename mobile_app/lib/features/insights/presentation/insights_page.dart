import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/insights_repository.dart';

class InsightsPage extends ConsumerWidget {
  const InsightsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoriasAsync = ref.watch(categoriasProvider);
    final resumoAsync = ref.watch(analiseResumoProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Insights IA')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          categoriasAsync.when(
            data: (categorias) => Card(
              child: ListTile(
                title: const Text('Categorias carregadas da API'),
                subtitle: Text(
                  'Despesa: ${categorias.despesa.length} • Receita: ${categorias.receita.length}',
                ),
              ),
            ),
            loading: () => const Card(child: ListTile(title: Text('Carregando categorias...'))),
            error: (error, stack) => Card(child: ListTile(title: Text(error.toString()))),
          ),
          const SizedBox(height: 12),
          resumoAsync.when(
            data: (resumo) => Card(
              child: ListTile(
                title: const Text('Resumo analitico'),
                subtitle: Text(
                  'Mes ref: ${resumo.anomeReferencia}\nGasto atual: R\$ ${resumo.metricas.gastoAtual.toStringAsFixed(2)}',
                ),
              ),
            ),
            loading: () => const Card(child: ListTile(title: Text('Carregando resumo...'))),
            error: (error, stack) => Card(child: ListTile(title: Text(error.toString()))),
          ),
        ],
      ),
    );
  }
}
