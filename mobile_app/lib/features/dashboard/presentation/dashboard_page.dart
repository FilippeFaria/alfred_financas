import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/formatters.dart';
import '../../../core/network/dto/transacao_dto.dart';
import '../data/dashboard_models.dart';
import '../data/dashboard_repository.dart';

class DashboardPage extends ConsumerStatefulWidget {
  const DashboardPage({super.key});

  @override
  ConsumerState<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends ConsumerState<DashboardPage> {
  String? _categoriaSelecionada;
  bool _detalharCategorias = false;
  int _mesesHistorico = 6;

  Future<void> _recarregar() async {
    final filtros = ref.read(dashboardFiltersProvider);
    final repository = ref.read(dashboardRepositoryProvider);
    await repository.carregarResumo(
      filtros: filtros,
      forceRefresh: true,
    );
    ref.invalidate(dashboardSnapshotProvider);
    await ref.read(dashboardSnapshotProvider.future);
  }

  @override
  Widget build(BuildContext context) {
    final filtros = ref.watch(dashboardFiltersProvider);
    final snapshotAsync = ref.watch(dashboardSnapshotProvider);
    final repository = ref.watch(dashboardRepositoryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Dashboard analítico')),
      body: RefreshIndicator(
        onRefresh: _recarregar,
        child: snapshotAsync.when(
          skipLoadingOnRefresh: true,
          skipError: true,
          data: (data) => _DashboardBody(
            data: data,
            filtros: filtros,
            categoriaSelecionada: _categoriaSelecionada,
            detalharCategorias: _detalharCategorias,
            mesesHistorico: _mesesHistorico,
            onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value),
            onDetalharCategoriasChanged: (value) => setState(() => _detalharCategorias = value),
            onMesesHistoricoChanged: (value) => setState(() => _mesesHistorico = value),
            onAtualizarFiltros: (novosFiltros) => ref.read(dashboardFiltersProvider.notifier).aplicar(novosFiltros),
          ),
          loading: () => const _DashboardSkeleton(),
          error: (error, stack) {
            final cache = repository.getCache(filtros);
            if (cache != null) {
              return _DashboardBody(
                data: cache,
                filtros: filtros,
                categoriaSelecionada: _categoriaSelecionada,
                detalharCategorias: _detalharCategorias,
                mesesHistorico: _mesesHistorico,
                onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value),
                onDetalharCategoriasChanged: (value) => setState(() => _detalharCategorias = value),
                onMesesHistoricoChanged: (value) => setState(() => _mesesHistorico = value),
                onAtualizarFiltros: (novosFiltros) => ref.read(dashboardFiltersProvider.notifier).aplicar(novosFiltros),
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
  const _DashboardBody({
    required this.data,
    required this.filtros,
    required this.categoriaSelecionada,
    required this.detalharCategorias,
    required this.mesesHistorico,
    required this.onCategoriaChanged,
    required this.onDetalharCategoriasChanged,
    required this.onMesesHistoricoChanged,
    required this.onAtualizarFiltros,
    this.avisoOffline,
  });

  final DashboardSnapshot data;
  final DashboardFilters filtros;
  final String? categoriaSelecionada;
  final bool detalharCategorias;
  final int mesesHistorico;
  final ValueChanged<String?> onCategoriaChanged;
  final ValueChanged<bool> onDetalharCategoriasChanged;
  final ValueChanged<int> onMesesHistoricoChanged;
  final ValueChanged<DashboardFilters> onAtualizarFiltros;
  final String? avisoOffline;

  @override
  Widget build(BuildContext context) {
    final selectedAnome = filtros.anomeReferencia ?? data.anomeReferencia;
    final anomeLabel = _formatarAnome(selectedAnome);
    final mesesVisiveis = _mesesVisiveis(data.items, selectedAnome, mesesHistorico);
    final despesasMes = _despesasDoMes(data.items, selectedAnome);
    final categoriasMes = _categoriasDoMes(despesasMes);
    final categoriasDisponiveis = categoriasMes.map((item) => item.nome).toList();
    final categoriaEfetiva = categoriasDisponiveis.contains(categoriaSelecionada)
        ? categoriaSelecionada
        : (categoriasDisponiveis.isNotEmpty ? categoriasDisponiveis.first : null);
    final evolucaoCategoria = categoriaEfetiva == null
        ? const <_SerieMensal>[]
        : _serieCategoria(data.items, categoriaEfetiva, mesesVisiveis);
    final tendenciaMeses = _serieTotal(data.items, mesesVisiveis);

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        _HeroCard(data: data, selectedMonthLabel: anomeLabel),
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
        _AnalysisFiltersCard(
          data: data,
          filtros: filtros,
          onAtualizarFiltros: onAtualizarFiltros,
        ),
        const SizedBox(height: 12),
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
                    title: 'Gasto mês anterior',
                    label: data.metricas.labelPrev,
                    value: formatarMoeda(data.metricas.gastoAnterior),
                    delta: _formatarDelta(data.metricas.deltaAnterior),
                    icon: Icons.arrow_back_outlined,
                    accentColor: const Color(0xFF8B5E00),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Gasto mês atual',
                    label: data.metricas.labelCurr,
                    value: formatarMoeda(data.metricas.gastoAtual),
                    delta: _formatarDelta(data.metricas.deltaAtual),
                    icon: Icons.trending_down_outlined,
                    accentColor: const Color(0xFF0E7A6D),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Média últimos 3 meses',
                    label: data.metricas.label3m,
                    value: formatarMoeda(data.metricas.gasto3mMedia),
                    delta: _formatarDelta(data.metricas.delta3m),
                    icon: Icons.insights_outlined,
                    accentColor: const Color(0xFF3142A4),
                  ),
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 12),
        _ResumoOrcamentoCard(data: data),
        const SizedBox(height: 12),
        _DistribuicaoCategoriaCard(
          categorias: categoriasMes,
          detalharCategorias: detalharCategorias,
          onDetalharCategoriasChanged: onDetalharCategoriasChanged,
        ),
        const SizedBox(height: 12),
        _EvolucaoCategoriaCard(
          categoria: categoriaEfetiva,
          categoriasDisponiveis: categoriasDisponiveis,
          mesesVisiveis: mesesVisiveis,
          evolucao: evolucaoCategoria,
          onCategoriaChanged: onCategoriaChanged,
          onMesesHistoricoChanged: onMesesHistoricoChanged,
          mesesHistorico: mesesHistorico,
        ),
        const SizedBox(height: 12),
        _TendenciaMensalCard(mesesVisiveis: mesesVisiveis, serie: tendenciaMeses),
        const SizedBox(height: 12),
        const _SectionTitle(
          title: 'Categorias em destaque',
          subtitle: 'As categorias que mais concentraram despesas no recorte escolhido.',
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

class _AnalysisFiltersCard extends StatelessWidget {
  const _AnalysisFiltersCard({
    required this.data,
    required this.filtros,
    required this.onAtualizarFiltros,
  });

  final DashboardSnapshot data;
  final DashboardFilters filtros;
  final ValueChanged<DashboardFilters> onAtualizarFiltros;

  String _labelMesSelecionado(int anome) => _formatarAnome(anome);

  @override
  Widget build(BuildContext context) {
    final selectedAnome = filtros.anomeReferencia ?? data.anomeReferencia;
    final options = <int>{
      ...data.anomesDisponiveis,
      selectedAnome,
    }.toList()
      ..sort();
    final index = options.indexWhere((item) => item == selectedAnome);
    final selectedIndex = index >= 0 ? index : options.length - 1;
    final maxIndex = (options.length - 1).clamp(0, 999).toDouble();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Filtros da análise',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 12),
            Text(
              'Mês selecionado: ${_labelMesSelecionado(options[selectedIndex])}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Slider(
              value: selectedIndex.toDouble(),
              min: 0,
              max: maxIndex,
              divisions: options.length > 1 ? options.length - 1 : null,
              label: _labelMesSelecionado(options[selectedIndex]),
              onChanged: options.length <= 1 ? null : (value) {},
              onChangeEnd: options.length <= 1
                  ? null
                  : (value) {
                      final chosen = options[value.round()];
                      onAtualizarFiltros(
                        filtros.copyWith(anomeReferencia: chosen, clearAnomeReferencia: false),
                      );
                    },
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  label: const Text('Grandes transações'),
                  selected: filtros.desconsiderar,
                  onSelected: (value) => onAtualizarFiltros(filtros.copyWith(desconsiderar: value)),
                ),
                FilterChip(
                  label: const Text('VA'),
                  selected: filtros.va,
                  onSelected: (value) => onAtualizarFiltros(filtros.copyWith(va: value)),
                ),
                FilterChip(
                  label: const Text('VR'),
                  selected: filtros.vr,
                  onSelected: (value) => onAtualizarFiltros(filtros.copyWith(vr: value)),
                ),
                FilterChip(
                  label: const Text('Bianca'),
                  selected: filtros.bianca,
                  onSelected: (value) => onAtualizarFiltros(filtros.copyWith(bianca: value)),
                ),
                FilterChip(
                  label: const Text('Filippe'),
                  selected: filtros.filippe,
                  onSelected: (value) => onAtualizarFiltros(filtros.copyWith(filippe: value)),
                ),
                FilterChip(
                  label: const Text('Dias do mês'),
                  selected: filtros.dayToDate,
                  onSelected: (value) => onAtualizarFiltros(filtros.copyWith(dayToDate: value)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ResumoOrcamentoCard extends StatelessWidget {
  const _ResumoOrcamentoCard({required this.data});

  final DashboardSnapshot data;

  @override
  Widget build(BuildContext context) {
    return Card(
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
              value: (data.orcamentoUsadoPercentual / 100).clamp(0, 1).toDouble(),
              minHeight: 10,
              borderRadius: BorderRadius.circular(999),
            ),
            const SizedBox(height: 8),
            Text(
              data.orcamentoUsadoLabel,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class _DistribuicaoCategoriaCard extends StatelessWidget {
  const _DistribuicaoCategoriaCard({
    required this.categorias,
    required this.detalharCategorias,
    required this.onDetalharCategoriasChanged,
  });

  final List<_CategoriaTotal> categorias;
  final bool detalharCategorias;
  final ValueChanged<bool> onDetalharCategoriasChanged;

  @override
  Widget build(BuildContext context) {
    final itens = detalharCategorias ? categorias : categorias.take(5).toList();
    final total = categorias.fold<double>(0, (sum, item) => sum + item.valor);
    final maxValor = categorias.isEmpty ? 0.0 : categorias.first.valor;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.donut_small_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Distribuição por categoria',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
                Switch(
                  value: detalharCategorias,
                  onChanged: onDetalharCategoriasChanged,
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              detalharCategorias ? 'Detalhando todas as categorias' : 'Mostrando as principais categorias',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (categorias.isEmpty)
              const ListTile(
                leading: Icon(Icons.label_off_outlined),
                title: Text('Sem despesas para exibir'),
                subtitle: Text('A distribuição aparece assim que o filtro encontrar dados.'),
              )
            else
              ...itens.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(child: Text(item.nome)),
                          Text(formatarMoeda(item.valor), style: const TextStyle(fontWeight: FontWeight.w700)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      LinearProgressIndicator(
                        value: maxValor <= 0 ? 0 : (item.valor / maxValor).clamp(0, 1).toDouble(),
                        minHeight: 10,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        total <= 0 ? '0%' : '${((item.valor / total) * 100).toStringAsFixed(1).replaceAll('.', ',')}%',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _EvolucaoCategoriaCard extends StatelessWidget {
  const _EvolucaoCategoriaCard({
    required this.categoria,
    required this.categoriasDisponiveis,
    required this.mesesVisiveis,
    required this.evolucao,
    required this.onCategoriaChanged,
    required this.onMesesHistoricoChanged,
    required this.mesesHistorico,
  });

  final String? categoria;
  final List<String> categoriasDisponiveis;
  final List<int> mesesVisiveis;
  final List<_SerieMensal> evolucao;
  final ValueChanged<String?> onCategoriaChanged;
  final ValueChanged<int> onMesesHistoricoChanged;
  final int mesesHistorico;

  @override
  Widget build(BuildContext context) {
    final maxValor = evolucao.isEmpty ? 0.0 : evolucao.map((e) => e.valor).reduce((a, b) => a > b ? a : b);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.show_chart),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Evolução de categoria',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              initialValue: categoria,
              decoration: const InputDecoration(labelText: 'Escolha a categoria'),
              items: categoriasDisponiveis
                  .map((item) => DropdownMenuItem<String?>(value: item, child: Text(item)))
                  .toList(),
              onChanged: onCategoriaChanged,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Meses no gráfico: $mesesHistorico',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                Text(
                  '$mesesHistorico',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                ),
              ],
            ),
            Slider(
              value: mesesHistorico.clamp(3, 12).toDouble(),
              min: 3,
              max: 12,
              divisions: 9,
              label: '$mesesHistorico meses',
              onChanged: (value) => onMesesHistoricoChanged(value.round().clamp(3, 12).toInt()),
            ),
            const SizedBox(height: 4),
            Text(
              'Período do gráfico: ${mesesVisiveis.length} meses',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (categoria == null || evolucao.isEmpty)
              const ListTile(
                leading: Icon(Icons.insights_outlined),
                title: Text('Escolha uma categoria para ver a evolução'),
                subtitle: Text('O gráfico usa o recorte do mês selecionado e o histórico visível.'),
              )
            else
              SizedBox(
                height: 180,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: evolucao
                      .map(
                        (item) => Expanded(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 4),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                Text(
                                  formatarMoeda(item.valor),
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                                const SizedBox(height: 4),
                                Container(
                                  height: maxValor <= 0
                                      ? 8
                                      : (120 * (item.valor / maxValor)).clamp(8, 120).toDouble(),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF0E7A6D),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  _formatarAnome(item.anome),
                                  textAlign: TextAlign.center,
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _TendenciaMensalCard extends StatelessWidget {
  const _TendenciaMensalCard({
    required this.mesesVisiveis,
    required this.serie,
  });

  final List<int> mesesVisiveis;
  final List<_SerieMensal> serie;

  @override
  Widget build(BuildContext context) {
    final maxValor = serie.isEmpty ? 0.0 : serie.map((e) => e.valor).reduce((a, b) => a > b ? a : b);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.bar_chart_outlined),
                const SizedBox(width: 8),
                Text(
                  'Tendência mensal',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Período: ${mesesVisiveis.length} meses',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            if (serie.isEmpty)
              const ListTile(
                leading: Icon(Icons.timeline_outlined),
                title: Text('Sem dados no período escolhido'),
              )
            else
              ...serie.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(child: Text(_formatarAnome(item.anome))),
                          Text(formatarMoeda(item.valor), style: const TextStyle(fontWeight: FontWeight.w700)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      LinearProgressIndicator(
                        value: maxValor <= 0 ? 0 : (item.valor / maxValor).clamp(0, 1).toDouble(),
                        minHeight: 10,
                        borderRadius: BorderRadius.circular(999),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.label,
    required this.value,
    required this.delta,
    required this.icon,
    required this.accentColor,
  });

  final String title;
  final String label;
  final String value;
  final String? delta;
  final IconData icon;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final deltaColor = delta == null
        ? Colors.grey.shade700
        : delta!.startsWith('-')
            ? const Color(0xFF0E7A6D)
            : const Color(0xFFB76E00);

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
            const SizedBox(height: 2),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
            ),
            const SizedBox(height: 6),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            if (delta != null) ...[
              const SizedBox(height: 4),
              Text(
                delta!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: deltaColor,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.data,
    required this.selectedMonthLabel,
  });

  final DashboardSnapshot data;
  final String selectedMonthLabel;

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
                          'Painel analítico',
                          style: theme.textTheme.titleLarge?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          'Visão rápida do caixa, orçamento e despesas no mês selecionado.',
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
              const SizedBox(height: 18),
              Text(
                'Mês em análise',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: Colors.white.withOpacity(0.85),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                selectedMonthLabel,
                style: theme.textTheme.headlineMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Saldo total: ${formatarMoeda(data.saldoTotal)}',
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
        _SkeletonBox(height: 260),
        SizedBox(height: 12),
        _SkeletonBox(height: 180),
        SizedBox(height: 12),
        _SkeletonBox(height: 180),
        SizedBox(height: 12),
        _SkeletonBox(height: 180),
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

String _formatarDelta(double? delta) {
  if (delta == null) {
    return 'Sem comparativo';
  }
  final sinal = delta >= 0 ? '+' : '-';
  return '$sinal${formatarPercentual(delta.abs() * 100)}';
}

String _formatarAnome(int anome) {
  final texto = anome.toString().padLeft(6, '0');
  return '${texto.substring(4, 6)}/${texto.substring(0, 4)}';
}

List<_CategoriaTotal> _categoriasDoMes(List<TransacaoDto> items) {
  final mapa = <String, double>{};
  for (final item in items) {
    if (item.tipo != 'Despesa') {
      continue;
    }
    final categoria = item.categoria.trim().isEmpty ? 'Sem categoria' : item.categoria;
    mapa[categoria] = (mapa[categoria] ?? 0) + item.valor.abs();
  }
  final categorias = mapa.entries
      .map((entry) => _CategoriaTotal(nome: entry.key, valor: entry.value))
      .toList()
    ..sort((a, b) => b.valor.compareTo(a.valor));
  return categorias;
}

List<TransacaoDto> _despesasDoMes(List<TransacaoDto> items, int anome) {
  return items.where((item) {
    if (item.tipo != 'Despesa') {
      return false;
    }
    final data = tentarConverterParaData(item.data);
    if (data == null) {
      return false;
    }
    return data.year * 100 + data.month == anome;
  }).toList();
}

List<int> _mesesVisiveis(List<TransacaoDto> items, int selectedAnome, int lookback) {
  final meses = items
      .map((item) => tentarConverterParaData(item.data))
      .whereType<DateTime>()
      .map((data) => data.year * 100 + data.month)
      .where((anome) => anome <= selectedAnome)
      .toSet()
      .toList()
    ..sort();

  if (meses.isEmpty) {
    return [selectedAnome];
  }

    final limite = lookback.clamp(3, 12).toInt();
  final selecionados = meses.length > limite ? meses.sublist(meses.length - limite) : meses;
  return selecionados;
}

List<_SerieMensal> _serieCategoria(List<TransacaoDto> items, String categoria, List<int> meses) {
  return meses
      .map(
        (anome) => _SerieMensal(
          anome: anome,
          valor: _totalCategoriaMes(items, categoria, anome),
        ),
      )
      .toList();
}

List<_SerieMensal> _serieTotal(List<TransacaoDto> items, List<int> meses) {
  return meses
      .map(
        (anome) => _SerieMensal(
          anome: anome,
          valor: _totalMes(items, anome),
        ),
      )
      .toList();
}

double _totalCategoriaMes(List<TransacaoDto> items, String categoria, int anome) {
  return items.fold<double>(0, (sum, item) {
    if (item.tipo != 'Despesa') {
      return sum;
    }
    final data = tentarConverterParaData(item.data);
    if (data == null || data.year * 100 + data.month != anome) {
      return sum;
    }
    final itemCategoria = item.categoria.trim().isEmpty ? 'Sem categoria' : item.categoria;
    if (itemCategoria != categoria) {
      return sum;
    }
    return sum + item.valor.abs();
  });
}

double _totalMes(List<TransacaoDto> items, int anome) {
  return items.fold<double>(0, (sum, item) {
    if (item.tipo != 'Despesa') {
      return sum;
    }
    final data = tentarConverterParaData(item.data);
    if (data == null || data.year * 100 + data.month != anome) {
      return sum;
    }
    return sum + item.valor.abs();
  });
}

class _CategoriaTotal {
  _CategoriaTotal({
    required this.nome,
    required this.valor,
  });

  final String nome;
  final double valor;
}

class _SerieMensal {
  _SerieMensal({
    required this.anome,
    required this.valor,
  });

  final int anome;
  final double valor;
}
