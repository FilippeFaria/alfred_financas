import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/formatters.dart';
import '../data/insights_repository.dart';

class InsightsPage extends ConsumerWidget {
  const InsightsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoriasAsync = ref.watch(categoriasProvider);
    final resumoAsync = ref.watch(analiseResumoProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Insights')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: const Color(0xFF0E7A6D).withValues(alpha: 0.08),
            child: const ListTile(
              leading: Icon(Icons.auto_awesome_outlined),
              title: Text('Análise automática pronta para evoluir'),
              subtitle: Text('Aqui ficam os resumos analíticos e os blocos que podem alimentar a IA.'),
            ),
          ),
          const SizedBox(height: 12),
          categoriasAsync.when(
            data: (categorias) => Card(
              child: ListTile(
                leading: const Icon(Icons.category_outlined),
                title: const Text('Categorias carregadas da API'),
                subtitle: Text(
                  'Despesa: ${categorias.despesa.length} • Receita: ${categorias.receita.length} • Investimento: ${categorias.investimento.length}',
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
                leading: const Icon(Icons.analytics_outlined),
                title: const Text('Resumo analítico'),
                subtitle: Text(
                  'Mês ref: ${resumo.anomeReferencia}\n'
                  'Gasto atual: ${formatarMoeda(resumo.metricas.gastoAtual)}\n'
                  'Média 3m: ${formatarMoeda(resumo.metricas.gasto3mMedia)}',
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
