import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/dashboard_models.dart';
import '../data/dashboard_repository.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(dashboardSnapshotProvider);
    final repository = ref.watch(dashboardRepositoryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Dashboard Financeiro')),
      body: RefreshIndicator(
        onRefresh: () async {
          await repository.carregarResumo(forceRefresh: true);
          ref.invalidate(dashboardSnapshotProvider);
          await ref.read(dashboardSnapshotProvider.future);
        },
        child: snapshot.when(
          data: (data) => _DashboardBody(data: data),
          loading: () => const _DashboardSkeleton(),
          error: (error, stack) {
            final cache = repository.cache;
            if (cache != null) {
              return _DashboardBody(
                data: cache,
                avisoOffline:
                    'Exibindo ultimo cache local. Nao foi possivel atualizar agora.',
              );
            }
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                const Text('Nao foi possivel conectar com a API.'),
                const SizedBox(height: 12),
                Text(error.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: () => ref.refresh(dashboardSnapshotProvider),
                  child: const Text('Tentar novamente'),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _DashboardBody extends StatelessWidget {
  const _DashboardBody({required this.data, this.avisoOffline});

  final DashboardSnapshot data;
  final String? avisoOffline;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        if (avisoOffline != null) ...[
          Card(
            color: Colors.amber.shade50,
            child: ListTile(
              leading: const Icon(Icons.wifi_off_outlined),
              title: Text(avisoOffline!),
            ),
          ),
          const SizedBox(height: 12),
        ],
        Card(
          child: ListTile(
            leading: const Icon(Icons.cloud_done_outlined),
            title: const Text('Status da API'),
            subtitle: Text(data.status.toUpperCase()),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _MetricCard(
                title: 'Saldo Total',
                value: 'R\$ ${data.saldoTotal.toStringAsFixed(2)}',
                icon: Icons.account_balance_wallet_outlined,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                title: 'Gastos do Mes',
                value: 'R\$ ${data.gastoMes.toStringAsFixed(2)}',
                icon: Icons.trending_down_outlined,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            leading: const Icon(Icons.pie_chart_outline),
            title: const Text('Orcamento usado'),
            subtitle: Text(data.orcamentoUsadoLabel),
            trailing: Text('${data.orcamentoUsadoPercentual.toStringAsFixed(1)}%'),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'Categorias em destaque',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        ...data.categoriasDestaque.map(
          (categoria) => Card(
            child: ListTile(
              leading: const Icon(Icons.label_outline),
              title: Text(categoria.nome),
              trailing: Text('R\$ ${categoria.valor.toStringAsFixed(2)}'),
            ),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'Ultimos lancamentos',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        ...data.ultimosLancamentos.map(
          (item) => Card(
            child: ListTile(
              title: Text(item.nome),
              subtitle: Text('${item.categoria} | ${item.data}'),
              trailing: Text('R\$ ${item.valor.toStringAsFixed(2)}'),
            ),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'Saldos por conta',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        ...data.saldos.map(
          (saldo) => Card(
            child: ListTile(
              title: Text(saldo.conta),
              trailing: Text('R\$ ${saldo.saldo.toStringAsFixed(2)}'),
            ),
          ),
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
  });

  final String title;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(value),
          ],
        ),
      ),
    );
  }
}

class _DashboardSkeleton extends StatelessWidget {
  const _DashboardSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: const [
        _SkeletonBox(height: 70),
        SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _SkeletonBox(height: 110)),
            SizedBox(width: 8),
            Expanded(child: _SkeletonBox(height: 110)),
          ],
        ),
        SizedBox(height: 8),
        _SkeletonBox(height: 70),
        SizedBox(height: 12),
        _SkeletonBox(height: 60),
        SizedBox(height: 8),
        _SkeletonBox(height: 60),
        SizedBox(height: 8),
        _SkeletonBox(height: 60),
      ],
    );
  }
}

class _SkeletonBox extends StatelessWidget {
  const _SkeletonBox({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(12),
      ),
    );
  }
}
