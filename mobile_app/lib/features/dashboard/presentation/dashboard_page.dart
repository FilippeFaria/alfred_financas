import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/formatters.dart';
import '../data/dashboard_models.dart';
import '../data/dashboard_repository.dart';

class DashboardPage extends ConsumerStatefulWidget {
  const DashboardPage({super.key});

  @override
  ConsumerState<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends ConsumerState<DashboardPage> {
  String? _categoriaSelecionada;
  int _mesesHistorico = 6;
  DashboardSnapshot? _ultimoSnapshotVisivel;
  bool _salvandoOrcamento = false;

  Future<void> _recarregar() async {
    final filtros = ref.read(dashboardFiltersProvider);
    final repository = ref.read(dashboardRepositoryProvider);
    final providerArgs = (
      filtros: filtros,
      categoria: _categoriaSelecionada,
      mesesHistorico: _mesesHistorico,
    );
    await repository.carregarResumo(
      filtros: filtros,
      categoria: _categoriaSelecionada,
      mesesHistorico: _mesesHistorico,
      forceRefresh: true,
    );
    ref.invalidate(dashboardSnapshotProvider(providerArgs));
    await ref.read(dashboardSnapshotProvider(providerArgs).future);
  }

  Future<void> _abrirEditorOrcamento(DashboardSnapshot data) async {
    final repository = ref.read(dashboardRepositoryProvider);
    final categoriasApi = await repository.carregarCategoriasDespesa();
    final orcamentoAtual = await repository.carregarOrcamentoAtual();
    final categorias = <String>{
      ...categoriasApi,
      ...orcamentoAtual.keys,
      ...data.categoriasDestaque.map((e) => e.nome),
    }.toList()
      ..sort();
    final valores = <String, double>{
      for (final categoria in categorias) categoria: orcamentoAtual[categoria] ?? 0.0,
    };

    if (!mounted) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(context).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Editar valores desejados',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 12),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: categorias.length,
                  itemBuilder: (context, index) {
                    final categoria = categorias[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: TextFormField(
                        initialValue: (valores[categoria] ?? 0.0).toStringAsFixed(2),
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: InputDecoration(
                          labelText: categoria,
                          border: const OutlineInputBorder(),
                        ),
                        onChanged: (value) {
                          final normalizado = value.replaceAll(',', '.').trim();
                          final parsed = double.tryParse(normalizado) ?? 0.0;
                          valores[categoria] = parsed < 0 ? 0.0 : parsed;
                        },
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _salvandoOrcamento
                      ? null
                      : () async {
                          Navigator.of(context).pop();
                          setState(() => _salvandoOrcamento = true);
                          try {
                            await repository.salvarOrcamento(valores);
                            await _recarregar();
                            if (!mounted) return;
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              const SnackBar(content: Text('Orçamento salvo com sucesso.')),
                            );
                          } catch (error) {
                            if (!mounted) return;
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(content: Text('Erro ao salvar orçamento: $error')),
                            );
                          } finally {
                            if (mounted) {
                              setState(() => _salvandoOrcamento = false);
                            }
                          }
                        },
                  icon: const Icon(Icons.save_outlined),
                  label: const Text('Salvar'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtros = ref.watch(dashboardFiltersProvider);
    final providerArgs = (
      filtros: filtros,
      categoria: _categoriaSelecionada,
      mesesHistorico: _mesesHistorico,
    );
    final snapshotAsync = ref.watch(dashboardSnapshotProvider(providerArgs));
    final repository = ref.watch(dashboardRepositoryProvider);
    snapshotAsync.whenData((data) => _ultimoSnapshotVisivel = data);

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
            mesesHistorico: _mesesHistorico,
            onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value == 'Todas' ? null : value),
            onMesesHistoricoChanged: (value) => setState(() => _mesesHistorico = value),
            onAtualizarFiltros: (novosFiltros) => ref.read(dashboardFiltersProvider.notifier).aplicar(novosFiltros),
            onEditarOrcamento: () => _abrirEditorOrcamento(data),
          ),
          loading: () {
            if (_ultimoSnapshotVisivel != null) {
              return _DashboardBody(
                data: _ultimoSnapshotVisivel!,
                filtros: filtros,
                categoriaSelecionada: _categoriaSelecionada,
                mesesHistorico: _mesesHistorico,
                onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value == 'Todas' ? null : value),
                onMesesHistoricoChanged: (value) => setState(() => _mesesHistorico = value),
                onAtualizarFiltros: (novosFiltros) => ref.read(dashboardFiltersProvider.notifier).aplicar(novosFiltros),
                onEditarOrcamento: () => _abrirEditorOrcamento(_ultimoSnapshotVisivel!),
                avisoOffline: 'Atualizando filtros...',
              );
            }
            return const _DashboardSkeleton();
          },
          error: (error, stack) {
            final cache = repository.getCache(
              filtros,
              categoria: _categoriaSelecionada,
              mesesHistorico: _mesesHistorico,
            );
            if (cache != null) {
              return _DashboardBody(
                data: cache,
                filtros: filtros,
                categoriaSelecionada: _categoriaSelecionada,
                mesesHistorico: _mesesHistorico,
                onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value == 'Todas' ? null : value),
                onMesesHistoricoChanged: (value) => setState(() => _mesesHistorico = value),
                onAtualizarFiltros: (novosFiltros) => ref.read(dashboardFiltersProvider.notifier).aplicar(novosFiltros),
                onEditarOrcamento: () => _abrirEditorOrcamento(cache),
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
                  onPressed: () => ref.refresh(dashboardSnapshotProvider(providerArgs)),
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
    required this.mesesHistorico,
    required this.onCategoriaChanged,
    required this.onMesesHistoricoChanged,
    required this.onAtualizarFiltros,
    required this.onEditarOrcamento,
    this.avisoOffline,
  });

  final DashboardSnapshot data;
  final DashboardFilters filtros;
  final String? categoriaSelecionada;
  final int mesesHistorico;
  final ValueChanged<String?> onCategoriaChanged;
  final ValueChanged<int> onMesesHistoricoChanged;
  final ValueChanged<DashboardFilters> onAtualizarFiltros;
  final VoidCallback onEditarOrcamento;
  final String? avisoOffline;

  @override
  Widget build(BuildContext context) {
    final selectedAnome = filtros.anomeReferencia ?? data.anomeReferencia;
    final anomeLabel = _formatarAnome(selectedAnome);
    final mesesVisiveis = data.serieMensal.map((item) => item.anome).toList();
    final categoriasMes = data.categoriasDestaque
        .map((item) => _CategoriaTotal(
              nome: item.nome,
              valor: item.valor,
              percentualOrcamento: item.percentualOrcamento,
            ))
        .toList();
    final categoriasDisponiveis = <String>[
      'Todas',
      ...data.categoriasDestaque.map((item) => item.nome),
    ].toSet().toList();
    final categoriaEfetiva = categoriaSelecionada ?? 'Todas';
    final evolucaoCategoria = data.serieCategoria
        .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
        .toList();
    final tendenciaMeses = data.serieMensal
        .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
        .toList();
    final evolucaoEfetiva = categoriaEfetiva == 'Todas' ? tendenciaMeses : evolucaoCategoria;

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
                    title: 'Gasto no mês anterior',
                    label: _formatarLabelPeriodo(data.metricas.labelPrev),
                    value: formatarMoeda(data.metricas.gastoAnterior),
                    delta: _formatarDelta(data.metricas.deltaAnterior, referencia: 'mês anterior'),
                    semanticState: _metricStateForDelta(data.metricas.deltaAnterior),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Gasto no mês atual',
                    label: _formatarLabelPeriodo(data.metricas.labelCurr),
                    value: formatarMoeda(data.metricas.gastoAtual),
                    delta: _formatarDelta(data.metricas.deltaAtual, referencia: 'mês anterior'),
                    semanticState: _metricStateForDelta(data.metricas.deltaAtual),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Média dos últimos 3 meses',
                    label: _formatarLabelPeriodo(data.metricas.label3m),
                    value: formatarMoeda(data.metricas.gasto3mMedia),
                    delta: _formatarDelta(data.metricas.delta3m, referencia: '3 meses anteriores'),
                    semanticState: _metricStateForDelta(data.metricas.delta3m),
                  ),
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 12),
        _ResumoOrcamentoCard(
          data: data,
          onEditarOrcamento: onEditarOrcamento,
        ),
        const SizedBox(height: 12),
        _DistribuicaoCategoriaCard(
          categorias: categoriasMes,
        ),
        const SizedBox(height: 12),
        _EvolucaoCategoriaCard(
          categoria: categoriaEfetiva,
          categoriasDisponiveis: categoriasDisponiveis,
          mesesVisiveis: mesesVisiveis,
          evolucao: evolucaoEfetiva,
          onCategoriaChanged: onCategoriaChanged,
        ),
        const SizedBox(height: 12),
        _TendenciaMensalCard(mesesVisiveis: mesesVisiveis, serie: tendenciaMeses),
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
                      ? const Color(0xFF0E7A6D).withValues(alpha: 0.12)
                      : const Color(0xFFB76E00).withValues(alpha: 0.12),
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
                  backgroundColor: Colors.black.withValues(alpha: 0.06),
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

class _AnalysisFiltersCard extends StatefulWidget {
  const _AnalysisFiltersCard({
    required this.data,
    required this.filtros,
    required this.onAtualizarFiltros,
  });

  final DashboardSnapshot data;
  final DashboardFilters filtros;
  final ValueChanged<DashboardFilters> onAtualizarFiltros;

  @override
  State<_AnalysisFiltersCard> createState() => _AnalysisFiltersCardState();
}

class _AnalysisFiltersCardState extends State<_AnalysisFiltersCard> {
  double? _sliderTempIndex;

  String _labelMesSelecionado(int anome) => _formatarAnome(anome);

  @override
  Widget build(BuildContext context) {
    final selectedAnome = widget.filtros.anomeReferencia ?? widget.data.anomeReferencia;
    final options = <int>{
      ...widget.data.anomesDisponiveis,
      selectedAnome,
    }.toList()
      ..sort();
    final index = options.indexWhere((item) => item == selectedAnome);
    final selectedIndex = index >= 0 ? index : options.length - 1;
    final maxIndex = (options.length - 1).clamp(0, 999).toDouble();
    final sliderValue = ((_sliderTempIndex ?? selectedIndex.toDouble()).clamp(0.0, maxIndex)).toDouble();

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
              value: sliderValue,
              min: 0,
              max: maxIndex,
              divisions: options.length > 1 ? options.length - 1 : null,
              label: _labelMesSelecionado(options[sliderValue.round()]),
              onChanged: options.length <= 1
                  ? null
                  : (value) {
                      setState(() => _sliderTempIndex = value);
                    },
              onChangeEnd: options.length <= 1
                  ? null
                  : (value) {
                      setState(() => _sliderTempIndex = null);
                      final chosen = options[value.round().clamp(0, options.length - 1)];
                      widget.onAtualizarFiltros(
                        widget.filtros.copyWith(anomeReferencia: chosen, clearAnomeReferencia: false),
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
                  selected: widget.filtros.desconsiderar,
                  onSelected: (value) => widget.onAtualizarFiltros(widget.filtros.copyWith(desconsiderar: value)),
                ),
                FilterChip(
                  label: const Text('VA'),
                  selected: widget.filtros.va,
                  onSelected: (value) => widget.onAtualizarFiltros(widget.filtros.copyWith(va: value)),
                ),
                FilterChip(
                  label: const Text('VR'),
                  selected: widget.filtros.vr,
                  onSelected: (value) => widget.onAtualizarFiltros(widget.filtros.copyWith(vr: value)),
                ),
                FilterChip(
                  label: const Text('Bianca'),
                  selected: widget.filtros.bianca,
                  onSelected: (value) => widget.onAtualizarFiltros(widget.filtros.copyWith(bianca: value)),
                ),
                FilterChip(
                  label: const Text('Filippe'),
                  selected: widget.filtros.filippe,
                  onSelected: (value) => widget.onAtualizarFiltros(widget.filtros.copyWith(filippe: value)),
                ),
                FilterChip(
                  label: const Text('Dias do mês'),
                  selected: widget.filtros.dayToDate,
                  onSelected: (value) => widget.onAtualizarFiltros(widget.filtros.copyWith(dayToDate: value)),
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
  const _ResumoOrcamentoCard({
    required this.data,
    required this.onEditarOrcamento,
  });

  final DashboardSnapshot data;
  final VoidCallback onEditarOrcamento;

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
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: onEditarOrcamento,
                  icon: const Icon(Icons.edit_outlined, size: 16),
                  label: const Text('Editar'),
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    minimumSize: const Size(0, 30),
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

class _DistribuicaoCategoriaCard extends StatefulWidget {
  const _DistribuicaoCategoriaCard({
    required this.categorias,
  });

  final List<_CategoriaTotal> categorias;

  @override
  State<_DistribuicaoCategoriaCard> createState() => _DistribuicaoCategoriaCardState();
}

class _DistribuicaoCategoriaCardState extends State<_DistribuicaoCategoriaCard> {
  bool _mostrarTodas = false;
  bool _modoPercentualOrcamento = false;

  Widget _buildCategoriaItem(BuildContext context, _CategoriaTotal item, double maxValor) {
    final percentualOrcamento = item.percentualOrcamento ?? 0.0;
    final usarPercentual = _modoPercentualOrcamento == true;
    final double valorBarra = usarPercentual
        ? (percentualOrcamento / 100).clamp(0, 1).toDouble()
        : (maxValor <= 0 ? 0.0 : (item.valor / maxValor).clamp(0, 1).toDouble());
    final valorDestaque = usarPercentual
        ? '${percentualOrcamento.toStringAsFixed(1).replaceAll('.', ',')}%'
        : formatarMoeda(item.valor);

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(item.nome)),
              Text(valorDestaque, style: const TextStyle(fontWeight: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: valorBarra,
            minHeight: 10,
            borderRadius: BorderRadius.circular(999),
          ),
          const SizedBox(height: 2),
          Text(
            item.percentualOrcamento == null
                ? 'Sem orçamento definido'
                : '${item.percentualOrcamento!.toStringAsFixed(1).replaceAll('.', ',')}% do orçamento da categoria',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final categorias = widget.categorias;
    final itensRestantes = categorias.length > 5 ? categorias.skip(5).toList() : const <_CategoriaTotal>[];
    final itensVisiveis = _mostrarTodas ? categorias : categorias.take(5).toList();
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
                  value: _modoPercentualOrcamento == true,
                  onChanged: (value) => setState(() => _modoPercentualOrcamento = value),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              _modoPercentualOrcamento
                  ? 'Barras em base 100 pelo percentual de uso do orçamento.'
                  : (itensRestantes.isEmpty
                      ? 'Mostrando as principais categorias'
                      : 'Mostrando as principais categorias. Expanda para ver as demais.'),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (categorias.isEmpty)
              const ListTile(
                leading: Icon(Icons.label_off_outlined),
                title: Text('Sem despesas para exibir'),
                subtitle: Text('A distribuição aparece assim que o filtro encontrar dados.'),
              )
            else ...[
              ...itensVisiveis.map((item) => _buildCategoriaItem(context, item, maxValor)),
              if (itensRestantes.isNotEmpty)
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => setState(() => _mostrarTodas = !_mostrarTodas),
                    icon: Icon(
                      _mostrarTodas ? Icons.expand_less : Icons.expand_more,
                      size: 16,
                    ),
                    style: TextButton.styleFrom(
                      foregroundColor: Colors.grey.shade600,
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      minimumSize: const Size(0, 30),
                    ),
                    label: Text(
                      _mostrarTodas ? 'Mostrar menos categorias' : 'Mostrar todas as categorias',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey.shade600,
                            fontWeight: FontWeight.w500,
                          ),
                    ),
                  ),
                ),
            ],
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
  });

  final String? categoria;
  final List<String> categoriasDisponiveis;
  final List<int> mesesVisiveis;
  final List<_SerieMensal> evolucao;
  final ValueChanged<String?> onCategoriaChanged;

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
            Text(
              'Período do gráfico: ${mesesVisiveis.length} meses',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (evolucao.isEmpty)
              const ListTile(
                leading: Icon(Icons.insights_outlined),
                title: Text('Sem dados para exibir evolução'),
                subtitle: Text('O gráfico usa o recorte do mês selecionado e o histórico visível.'),
              )
            else
              SizedBox(
                height: 190,
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
                                FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Text(
                                    formatarMoeda(item.valor),
                                    maxLines: 1,
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Container(
                                  width: 10,
                                  height: 10,
                                  decoration: const BoxDecoration(
                                    color: Color(0xFF0E7A6D),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Container(
                                  height: maxValor <= 0
                                      ? 8
                                      : (108 * (item.valor / maxValor)).clamp(8, 108).toDouble(),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF0E7A6D),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Text(
                                    _formatarAnome(item.anome),
                                    textAlign: TextAlign.center,
                                    maxLines: 1,
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
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
    required this.semanticState,
  });

  final String title;
  final String label;
  final String value;
  final String? delta;
  final _MetricSemanticState semanticState;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundColor: semanticState.background,
                  child: Icon(semanticState.icon, color: semanticState.foreground, size: 18),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              value,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w900,
                height: 1.0,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            if (delta != null)
              Row(
                children: [
                  Icon(semanticState.icon, size: 18, color: semanticState.foreground),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      delta!,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: semanticState.foreground,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
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
                            color: Colors.white.withValues(alpha: 0.9),
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
                  color: Colors.white.withValues(alpha: 0.85),
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
                  color: Colors.white.withValues(alpha: 0.9),
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
        color: Colors.white.withValues(alpha: 0.14),
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

String _formatarDelta(double? delta, {required String referencia}) {
  if (delta == null) {
    return 'Sem comparativo';
  }
  final percentual = formatarPercentual(delta.abs() * 100);
  if (delta < 0) {
    return '$percentual menor que o $referencia';
  }
  return '$percentual maior que o $referencia';
}

String _formatarAnome(int anome) {
  final texto = anome.toString().padLeft(6, '0');
  return '${_abreviarMes(int.parse(texto.substring(4, 6)))}/${texto.substring(0, 4)}';
}

String _formatarLabelPeriodo(String label) {
  if (label.contains(' - ')) {
    final partes = label.split(' - ');
    if (partes.length == 2) {
      final inicio = partes.first.trim().split('/');
      final fim = partes.last.trim().split('/');
      if (inicio.length == 2 && fim.length == 2) {
        return '${_abreviarMes(int.tryParse(inicio[0]) ?? 1)}–${_abreviarMes(int.tryParse(fim[0]) ?? 1)}/${fim[1]}';
      }
    }
  }
  final match = RegExp(r'^(\d{2})/(\d{4})$').firstMatch(label.trim());
  if (match != null) {
    return '${_abreviarMes(int.parse(match.group(1)!))}/${match.group(2)}';
  }
  return label;
}

String _abreviarMes(int mes) {
  const meses = <int, String>{
    1: 'Jan',
    2: 'Fev',
    3: 'Mar',
    4: 'Abr',
    5: 'Mai',
    6: 'Jun',
    7: 'Jul',
    8: 'Ago',
    9: 'Set',
    10: 'Out',
    11: 'Nov',
    12: 'Dez',
  };
  return meses[mes] ?? 'M$mes';
}

_MetricSemanticState _metricStateForDelta(double? delta) {
  if (delta == null) {
    return _MetricSemanticState.neutral();
  }
  if (delta < 0) {
    return _MetricSemanticState.success();
  }
  return _MetricSemanticState.alert();
}

class _MetricSemanticState {
  const _MetricSemanticState({
    required this.foreground,
    required this.background,
    required this.icon,
  });

  factory _MetricSemanticState.success() {
    return const _MetricSemanticState(
      foreground: Color(0xFF0E7A6D),
      background: Color(0xFFE7F8F5),
      icon: Icons.arrow_downward_rounded,
    );
  }

  factory _MetricSemanticState.alert() {
    return const _MetricSemanticState(
      foreground: Color(0xFFC62828),
      background: Color(0xFFFFE7E7),
      icon: Icons.arrow_upward_rounded,
    );
  }

  factory _MetricSemanticState.neutral() {
    return const _MetricSemanticState(
      foreground: Color(0xFF475569),
      background: Color(0xFFF1F5F9),
      icon: Icons.remove_rounded,
    );
  }

  final Color foreground;
  final Color background;
  final IconData icon;
}

class _CategoriaTotal {
  _CategoriaTotal({
    required this.nome,
    required this.valor,
    this.percentualOrcamento,
  });

  final String nome;
  final double valor;
  final double? percentualOrcamento;
}

class _SerieMensal {
  _SerieMensal({
    required this.anome,
    required this.valor,
  });

  final int anome;
  final double valor;
}
