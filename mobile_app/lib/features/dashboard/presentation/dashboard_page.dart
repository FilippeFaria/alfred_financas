import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/formatters.dart';
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
                avisoOffline: 'Exibindo último cache local. Não foi possível atualizar agora.',
              );
            }
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.cloud_off_outlined),
                    title: Text('Não foi possível conectar com a API.'),
                    subtitle: Text('Tente novamente em instantes ou confira a URL configurada.'),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(error.toString()),
                  ),
                ),
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
        _HeroCard(data: data),
        const SizedBox(height: 12),
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
        LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = constraints.maxWidth >= 520
                ? (constraints.maxWidth - 12) / 2
                : constraints.maxWidth;

            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Saldo total',
                    value: formatarMoeda(data.saldoTotal),
                    icon: Icons.account_balance_wallet_outlined,
                    accentColor: const Color(0xFF0E7A6D),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Gastos do mês',
                    value: formatarMoeda(data.gastoMes),
                    icon: Icons.trending_down_outlined,
                    accentColor: const Color(0xFFB76E00),
                  ),
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.pie_chart_outline),
                    const SizedBox(width: 8),
                    Text(
                      'Orçamento usado',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const Spacer(),
                    Text(
                      formatarPercentual(data.orcamentoUsadoPercentual),
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: (data.orcamentoUsadoPercentual / 100).clamp(0, 1),
                  minHeight: 10,
                  borderRadius: BorderRadius.circular(999),
                ),
                const SizedBox(height: 8),
                Text(
                  'Base média 3 meses: ${data.orcamentoUsadoLabel.replaceFirst('Base media 3 meses: ', '')}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        const _SectionTitle(
          title: 'Categorias em destaque',
          subtitle: 'Onde o dinheiro mais concentrou nos últimos lançamentos.',
        ),
        const SizedBox(height: 8),
        if (data.categoriasDestaque.isEmpty)
          const Card(
            child: ListTile(
              leading: Icon(Icons.label_off_outlined),
              title: Text('Sem categorias para destacar'),
              subtitle: Text('Assim que houver dados recentes, os destaques aparecem aqui.'),
            ),
          )
        else
          ...data.categoriasDestaque.map(
            (categoria) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: const Color(0xFF0E7A6D).withOpacity(0.12),
                    child: const Icon(Icons.label_outline, color: Color(0xFF0E7A6D)),
                  ),
                  title: Text(categoria.nome),
                  subtitle: const Text('Volume total'),
                  trailing: Text(
                    formatarMoeda(categoria.valor),
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ),
          ),
        const SizedBox(height: 12),
        const _SectionTitle(
          title: 'Últimos lançamentos',
          subtitle: 'Resumo do que entrou e saiu recentemente.',
        ),
        const SizedBox(height: 8),
        ...data.ultimosLancamentos.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: item.valor >= 0
                      ? const Color(0xFF0E7A6D).withOpacity(0.12)
                      : const Color(0xFFB76E00).withOpacity(0.12),
                  child: Icon(
                    item.valor >= 0 ? Icons.arrow_upward : Icons.arrow_downward,
                    color: item.valor >= 0 ? const Color(0xFF0E7A6D) : const Color(0xFFB76E00),
                  ),
                ),
                title: Text(item.nome),
                subtitle: Text(
                  '${item.categoria.isEmpty ? 'Sem categoria' : item.categoria} • ${formatarDataCurta(item.data)}',
                ),
                trailing: Text(
                  formatarMoeda(item.valor),
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: item.valor >= 0 ? const Color(0xFF0E7A6D) : const Color(0xFFB76E00),
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        const _SectionTitle(
          title: 'Saldos por conta',
          subtitle: 'A visão rápida de onde o dinheiro está agora.',
        ),
        const SizedBox(height: 8),
        ...data.saldos.map(
          (saldo) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: Colors.black.withOpacity(0.06),
                  child: const Icon(Icons.account_balance_outlined),
                ),
                title: Text(saldo.conta),
                trailing: Text(
                  formatarMoeda(saldo.saldo),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
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
    required this.accentColor,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              backgroundColor: accentColor.withOpacity(0.12),
              child: Icon(icon, color: accentColor),
            ),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.data});

  final DashboardSnapshot data;

  @override
  Widget build(BuildContext context) {
    final isOnline = data.status.toLowerCase() == 'ok';
    final theme = Theme.of(context);

    return Card(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isOnline
                ? const [Color(0xFF0E7A6D), Color(0xFF18A189)]
                : const [Color(0xFF1E293B), Color(0xFF334155)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const CircleAvatar(
                    backgroundColor: Colors.white24,
                    child: Icon(Icons.savings_outlined, color: Colors.white),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Painel financeiro',
                          style: theme.textTheme.titleLarge?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          'Visão rápida do caixa, orçamento e últimos movimentos.',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: Colors.white.withOpacity(0.9),
                          ),
                        ),
                      ],
                    ),
                  ),
                  _StatusChip(
                    label: isOnline ? 'Online' : data.status.toUpperCase(),
                    color: isOnline ? const Color(0xFF7CF2C8) : const Color(0xFFF7C46C),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Saldo total',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: Colors.white.withOpacity(0.85),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                formatarMoeda(data.saldoTotal),
                style: theme.textTheme.headlineMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Base média 3 meses: ${data.orcamentoUsadoLabel.replaceFirst('Base media 3 meses: ', '')}',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.white.withOpacity(0.9),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white24),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(
          label,
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          style: theme.textTheme.bodyMedium,
        ),
      ],
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
        _SkeletonBox(height: 220),
        SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _SkeletonBox(height: 122)),
            SizedBox(width: 8),
            Expanded(child: _SkeletonBox(height: 122)),
          ],
        ),
        SizedBox(height: 12),
        _SkeletonBox(height: 80),
        SizedBox(height: 12),
        _SkeletonBox(height: 92),
        SizedBox(height: 8),
        _SkeletonBox(height: 92),
        SizedBox(height: 8),
        _SkeletonBox(height: 92),
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
