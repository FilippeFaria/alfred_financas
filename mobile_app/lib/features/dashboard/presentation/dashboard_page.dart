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
  bool _detalharCategorias = false;
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
            detalharCategorias: _detalharCategorias,
            mesesHistorico: _mesesHistorico,
            onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value),
            onDetalharCategoriasChanged: (value) => setState(() => _detalharCategorias = value),
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
                detalharCategorias: _detalharCategorias,
                mesesHistorico: _mesesHistorico,
                onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value),
                onDetalharCategoriasChanged: (value) => setState(() => _detalharCategorias = value),
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
                detalharCategorias: _detalharCategorias,
                mesesHistorico: _mesesHistorico,
                onCategoriaChanged: (value) => setState(() => _categoriaSelecionada = value),
                onDetalharCategoriasChanged: (value) => setState(() => _detalharCategorias = value),
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
    required this.detalharCategorias,
    required this.mesesHistorico,
    required this.onCategoriaChanged,
    required this.onDetalharCategoriasChanged,
    required this.onMesesHistoricoChanged,
    required this.onAtualizarFiltros,
    required this.onEditarOrcamento,
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
    final categoriasDisponiveis = data.categoriasDestaque.map((item) => item.nome).toList();
    final categoriaEfetiva = categoriasDisponiveis.contains(categoriaSelecionada)
        ? categoriaSelecionada
        : (categoriasDisponiveis.isNotEmpty ? categoriasDisponiveis.first : null);
    final evolucaoCategoria = data.serieCategoria
        .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
        .toList();
    final tendenciaMeses = data.serieMensal
        .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
        .toList();

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
        _ResumoOrcamentoCard(
          data: data,
          onEditarOrcamento: onEditarOrcamento,
        ),
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
                    backgroundColor: const Color(0xFF0E7A6D).withValues(alpha: 0.12),
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
                        item.percentualOrcamento == null
                            ? 'Sem orçamento definido'
                            : '${item.percentualOrcamento!.toStringAsFixed(1).replaceAll('.', ',')}% do orçamento da categoria',
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
              backgroundColor: accentColor.withValues(alpha: 0.12),
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
