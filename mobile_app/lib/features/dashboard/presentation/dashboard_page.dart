import 'dart:math' as math;

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
  DashboardSnapshot? _ultimoSnapshotVisivel;
  DashboardSnapshot? _ultimoSnapshotEvolucaoVisivel;
  bool _salvandoOrcamento = false;

  Future<void> _recarregar() async {
    final filtros = ref.read(dashboardFiltersProvider);
    final repository = ref.read(dashboardRepositoryProvider);
    final ({DashboardFilters filtros, String? categoria, int mesesHistorico})
        providerArgsGeral = (
      filtros: filtros,
      categoria: null,
      mesesHistorico: 6,
    );
    final providerArgsEvolucao = (
      filtros: filtros,
      categoria: _categoriaSelecionada,
      mesesHistorico: 6,
    );
    await Future.wait([
      repository.carregarResumo(
        filtros: filtros,
        categoria: null,
        mesesHistorico: 6,
        forceRefresh: true,
      ),
      repository.carregarResumo(
        filtros: filtros,
        categoria: _categoriaSelecionada,
        mesesHistorico: 6,
        forceRefresh: true,
      ),
    ]);
    ref.invalidate(dashboardSnapshotProvider(providerArgsGeral));
    ref.invalidate(dashboardSnapshotProvider(providerArgsEvolucao));
    await Future.wait([
      ref.read(dashboardSnapshotProvider(providerArgsGeral).future),
      ref.read(dashboardSnapshotProvider(providerArgsEvolucao).future),
    ]);
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
      for (final categoria in categorias)
        categoria: orcamentoAtual[categoria] ?? 0.0,
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
                        initialValue:
                            (valores[categoria] ?? 0.0).toStringAsFixed(2),
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
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
                              const SnackBar(
                                  content:
                                      Text('Orçamento salvo com sucesso.')),
                            );
                          } catch (error) {
                            if (!mounted) return;
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(
                                  content:
                                      Text('Erro ao salvar orçamento: $error')),
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
    final ({DashboardFilters filtros, String? categoria, int mesesHistorico})
        providerArgsGeral = (
      filtros: filtros,
      categoria: null,
      mesesHistorico: 6,
    );
    final providerArgsEvolucao = (
      filtros: filtros,
      categoria: _categoriaSelecionada,
      mesesHistorico: 6,
    );
    final snapshotAsync = ref.watch(dashboardSnapshotProvider(providerArgsGeral));
    final snapshotEvolucaoAsync =
        ref.watch(dashboardSnapshotProvider(providerArgsEvolucao));
    final repository = ref.watch(dashboardRepositoryProvider);
    snapshotAsync.whenData((data) => _ultimoSnapshotVisivel = data);
    snapshotEvolucaoAsync.whenData((data) => _ultimoSnapshotEvolucaoVisivel = data);

    return Scaffold(
      appBar: AppBar(title: const Text('Dashboard analítico')),
      body: RefreshIndicator(
        onRefresh: _recarregar,
        child: snapshotAsync.when(
          skipLoadingOnRefresh: true,
          skipError: true,
          data: (data) => _DashboardBody(
            data: data,
            dataEvolucaoFiltrada:
                snapshotEvolucaoAsync.valueOrNull ??
                _ultimoSnapshotEvolucaoVisivel ??
                data,
            filtros: filtros,
            categoriaSelecionada: _categoriaSelecionada,
            onCategoriaChanged: (value) => setState(
                () => _categoriaSelecionada = value == 'Todas' ? null : value),
            onAtualizarFiltros: (novosFiltros) => ref
                .read(dashboardFiltersProvider.notifier)
                .aplicar(novosFiltros),
            onEditarOrcamento: () => _abrirEditorOrcamento(data),
          ),
          loading: () {
            if (_ultimoSnapshotVisivel != null) {
              return _DashboardBody(
                data: _ultimoSnapshotVisivel!,
                dataEvolucaoFiltrada:
                    snapshotEvolucaoAsync.valueOrNull ??
                    _ultimoSnapshotEvolucaoVisivel ??
                    _ultimoSnapshotVisivel!,
                filtros: filtros,
                categoriaSelecionada: _categoriaSelecionada,
                onCategoriaChanged: (value) => setState(() =>
                    _categoriaSelecionada = value == 'Todas' ? null : value),
                onAtualizarFiltros: (novosFiltros) => ref
                    .read(dashboardFiltersProvider.notifier)
                    .aplicar(novosFiltros),
                onEditarOrcamento: () =>
                    _abrirEditorOrcamento(_ultimoSnapshotVisivel!),
                avisoOffline: 'Atualizando filtros...',
              );
            }
            return const _DashboardSkeleton();
          },
          error: (error, stack) {
            final cache = repository.getCache(
              filtros,
              categoria: null,
              mesesHistorico: 6,
            );
            if (cache != null) {
              final cacheEvolucao = repository.getCache(
                    filtros,
                    categoria: _categoriaSelecionada,
                    mesesHistorico: 6,
                  ) ??
                  cache;
              return _DashboardBody(
                data: cache,
                dataEvolucaoFiltrada: cacheEvolucao,
                filtros: filtros,
                categoriaSelecionada: _categoriaSelecionada,
                onCategoriaChanged: (value) => setState(() =>
                    _categoriaSelecionada = value == 'Todas' ? null : value),
                onAtualizarFiltros: (novosFiltros) => ref
                    .read(dashboardFiltersProvider.notifier)
                    .aplicar(novosFiltros),
                onEditarOrcamento: () => _abrirEditorOrcamento(cache),
                avisoOffline:
                    'Exibindo último cache local. Não foi possível atualizar agora.',
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
                    subtitle: Text(
                        'Tente novamente em instantes ou confira a URL configurada.'),
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
                  onPressed: () => _recarregar(),
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
    required this.dataEvolucaoFiltrada,
    required this.filtros,
    required this.categoriaSelecionada,
    required this.onCategoriaChanged,
    required this.onAtualizarFiltros,
    required this.onEditarOrcamento,
    this.avisoOffline,
  });

  final DashboardSnapshot data;
  final DashboardSnapshot dataEvolucaoFiltrada;
  final DashboardFilters filtros;
  final String? categoriaSelecionada;
  final ValueChanged<String?> onCategoriaChanged;
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
      ...{
        ...data.categoriasDestaque.map((item) => item.nome),
      }.toList()
        ..sort(),
    ];
    final categoriaEfetiva = categoriaSelecionada ?? 'Todas';
    final evolucaoCategoria = dataEvolucaoFiltrada.serieCategoria
        .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
        .toList();
    final tendenciaMeses = data.serieMensal
        .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
        .toList();
    final evolucaoDespesasMes = dataEvolucaoFiltrada.serieEvolucaoDespesasMes
        .map(
          (item) => _EvolucaoDespesaDia(
            anome: item.anome,
            diaMes: item.diaMes,
            cumulativo: item.cumulativo,
          ),
        )
        .toList();
    final evolucaoEfetiva =
        categoriaEfetiva == 'Todas' ? tendenciaMeses : evolucaoCategoria;

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
                    delta: _formatarDelta(data.metricas.deltaAnterior,
                        referencia: 'mês anterior'),
                    semanticState:
                        _metricStateForDelta(data.metricas.deltaAnterior),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Gasto no mês atual',
                    label: _formatarLabelPeriodo(data.metricas.labelCurr),
                    value: formatarMoeda(data.metricas.gastoAtual),
                    delta: _formatarDelta(data.metricas.deltaAtual,
                        referencia: 'mês anterior'),
                    semanticState:
                        _metricStateForDelta(data.metricas.deltaAtual),
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _MetricCard(
                    title: 'Média dos últimos 3 meses',
                    label: _formatarLabelPeriodo(data.metricas.label3m),
                    value: formatarMoeda(data.metricas.gasto3mMedia),
                    delta: _formatarDelta(data.metricas.delta3m,
                        referencia: '3 meses anteriores'),
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
        _FiltroCategoriaEvolucaoCard(
          categoriaSelecionada: categoriaEfetiva,
          categoriasDisponiveis: categoriasDisponiveis,
          onCategoriaChanged: onCategoriaChanged,
        ),
        const SizedBox(height: 12),
        _EvolucaoCategoriaCard(
          mesesVisiveis: mesesVisiveis,
          evolucao: evolucaoEfetiva,
        ),
        const SizedBox(height: 12),
        _EvolucaoDespesasMesCard(
          categoriaSelecionada: categoriaEfetiva,
          evolucao: evolucaoDespesasMes,
          aplicarFiltroDiaDoMes: filtros.dayToDate,
        ),
        const SizedBox(height: 12),
        _TendenciaMensalCard(
          mesesVisiveis: mesesVisiveis,
          despesas: tendenciaMeses,
          receitas: data.serieReceitasMensal
              .map((item) => _SerieMensal(anome: item.anome, valor: item.valor))
              .toList(),
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
                    color: item.valor >= 0
                        ? const Color(0xFF0E7A6D)
                        : const Color(0xFFB76E00),
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
                    color: item.valor >= 0
                        ? const Color(0xFF0E7A6D)
                        : const Color(0xFFB76E00),
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
    final selectedAnome =
        widget.filtros.anomeReferencia ?? widget.data.anomeReferencia;
    final options = <int>{
      ...widget.data.anomesDisponiveis,
      selectedAnome,
    }.toList()
      ..sort();
    final index = options.indexWhere((item) => item == selectedAnome);
    final selectedIndex = index >= 0 ? index : options.length - 1;
    final maxIndex = (options.length - 1).clamp(0, 999).toDouble();
    final sliderValue =
        ((_sliderTempIndex ?? selectedIndex.toDouble()).clamp(0.0, maxIndex))
            .toDouble();

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
                      final chosen =
                          options[value.round().clamp(0, options.length - 1)];
                      widget.onAtualizarFiltros(
                        widget.filtros.copyWith(
                            anomeReferencia: chosen,
                            clearAnomeReferencia: false),
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
                  onSelected: (value) => widget.onAtualizarFiltros(
                      widget.filtros.copyWith(desconsiderar: value)),
                ),
                FilterChip(
                  label: const Text('VA'),
                  selected: widget.filtros.va,
                  onSelected: (value) => widget
                      .onAtualizarFiltros(widget.filtros.copyWith(va: value)),
                ),
                FilterChip(
                  label: const Text('VR'),
                  selected: widget.filtros.vr,
                  onSelected: (value) => widget
                      .onAtualizarFiltros(widget.filtros.copyWith(vr: value)),
                ),
                FilterChip(
                  label: const Text('Bianca'),
                  selected: widget.filtros.bianca,
                  onSelected: (value) => widget.onAtualizarFiltros(
                      widget.filtros.copyWith(bianca: value)),
                ),
                FilterChip(
                  label: const Text('Filippe'),
                  selected: widget.filtros.filippe,
                  onSelected: (value) => widget.onAtualizarFiltros(
                      widget.filtros.copyWith(filippe: value)),
                ),
                FilterChip(
                  label: const Text('Dias do mês'),
                  selected: widget.filtros.dayToDate,
                  onSelected: (value) => widget.onAtualizarFiltros(
                      widget.filtros.copyWith(dayToDate: value)),
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
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
              value:
                  (data.orcamentoUsadoPercentual / 100).clamp(0, 1).toDouble(),
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
  State<_DistribuicaoCategoriaCard> createState() =>
      _DistribuicaoCategoriaCardState();
}

class _DistribuicaoCategoriaCardState
    extends State<_DistribuicaoCategoriaCard> {
  bool _mostrarTodas = false;
  bool _modoPercentualOrcamento = false;

  Widget _buildCategoriaItem(
      BuildContext context, _CategoriaTotal item, double maxValor) {
    final percentualOrcamento = item.percentualOrcamento ?? 0.0;
    final usarPercentual = _modoPercentualOrcamento == true;
    final double valorBarra = usarPercentual
        ? (percentualOrcamento / 100).clamp(0, 1).toDouble()
        : (maxValor <= 0
            ? 0.0
            : (item.valor / maxValor).clamp(0, 1).toDouble());
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
              Text(valorDestaque,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
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
    final itensRestantes = categorias.length > 5
        ? categorias.skip(5).toList()
        : const <_CategoriaTotal>[];
    final itensVisiveis =
        _mostrarTodas ? categorias : categorias.take(5).toList();
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
                  onChanged: (value) =>
                      setState(() => _modoPercentualOrcamento = value),
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
                subtitle: Text(
                    'A distribuição aparece assim que o filtro encontrar dados.'),
              )
            else ...[
              ...itensVisiveis
                  .map((item) => _buildCategoriaItem(context, item, maxValor)),
              if (itensRestantes.isNotEmpty)
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () =>
                        setState(() => _mostrarTodas = !_mostrarTodas),
                    icon: Icon(
                      _mostrarTodas ? Icons.expand_less : Icons.expand_more,
                      size: 16,
                    ),
                    style: TextButton.styleFrom(
                      foregroundColor: Colors.grey.shade600,
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      minimumSize: const Size(0, 30),
                    ),
                    label: Text(
                      _mostrarTodas
                          ? 'Mostrar menos categorias'
                          : 'Mostrar todas as categorias',
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

class _FiltroCategoriaEvolucaoCard extends StatelessWidget {
  const _FiltroCategoriaEvolucaoCard({
    required this.categoriaSelecionada,
    required this.categoriasDisponiveis,
    required this.onCategoriaChanged,
  });

  final String categoriaSelecionada;
  final List<String> categoriasDisponiveis;
  final ValueChanged<String?> onCategoriaChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.blueGrey.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.filter_alt_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Filtro da seção de evolução',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Este filtro afeta apenas os 2 gráficos abaixo: Evolução de categoria e Evolução despesas no mês.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: categoriaSelecionada,
              decoration: const InputDecoration(
                labelText: 'Escolha a categoria (somente seção de evolução)',
              ),
              items: categoriasDisponiveis
                  .map(
                    (item) => DropdownMenuItem<String>(
                      value: item,
                      child: Text(item),
                    ),
                  )
                  .toList(),
              onChanged: onCategoriaChanged,
            ),
          ],
        ),
      ),
    );
  }
}

class _EvolucaoDespesasMesCard extends StatefulWidget {
  const _EvolucaoDespesasMesCard({
    required this.categoriaSelecionada,
    required this.evolucao,
    required this.aplicarFiltroDiaDoMes,
  });

  final String categoriaSelecionada;
  final List<_EvolucaoDespesaDia> evolucao;
  final bool aplicarFiltroDiaDoMes;

  @override
  State<_EvolucaoDespesasMesCard> createState() =>
      _EvolucaoDespesasMesCardState();
}

class _EvolucaoDespesasMesCardState extends State<_EvolucaoDespesasMesCard> {
  _PontoEvolucaoSelecionado? _selecionado;

  @override
  void didUpdateWidget(covariant _EvolucaoDespesasMesCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selecionado == null) {
      return;
    }
    final aindaExiste = widget.evolucao.any(
      (item) =>
          item.anome == _selecionado!.anome &&
          item.diaMes == _selecionado!.diaMes &&
          item.cumulativo == _selecionado!.cumulativo,
    );
    if (!aindaExiste) {
      _selecionado = null;
    }
  }

  void _atualizarSelecaoPorPosicao(
    Offset localPosition,
    List<_ProjectedEvolucaoPoint> projectedPoints,
  ) {
    final hit = _findNearestPoint(
      localPosition,
      projectedPoints,
      maxDistance: 18,
    );
    final proximo = hit == null
        ? null
        : _PontoEvolucaoSelecionado(
            anome: hit.anome,
            diaMes: hit.diaMes,
            cumulativo: hit.cumulativo,
            color: hit.color,
          );
    if (proximo == _selecionado) {
      return;
    }
    setState(() => _selecionado = proximo);
  }

  @override
  Widget build(BuildContext context) {
    final seriesMap = <int, List<_EvolucaoDespesaDia>>{};
    for (final item in widget.evolucao) {
      seriesMap
          .putIfAbsent(item.anome, () => <_EvolucaoDespesaDia>[])
          .add(item);
    }

    final series = seriesMap.entries
        .map(
          (entry) => _SerieEvolucaoMes(
            anome: entry.key,
            pontos: (entry.value..sort((a, b) => a.diaMes.compareTo(b.diaMes))),
          ),
        )
        .toList()
      ..sort((a, b) => a.anome.compareTo(b.anome));
    final maxDiaGlobal = series.fold<int>(0, (acc, serie) {
      if (serie.pontos.isEmpty) return acc;
      final ultimoDia = serie.pontos.last.diaMes;
      return ultimoDia > acc ? ultimoDia : acc;
    });
    final anomeMaisRecente = series.isEmpty ? null : series.last.anome;
    final pontosMesRecente = anomeMaisRecente == null
        ? const <_EvolucaoDespesaDia>[]
        : (series.firstWhere((item) => item.anome == anomeMaisRecente).pontos);
    final diaLimiteFiltro = pontosMesRecente.isNotEmpty
        ? pontosMesRecente.last.diaMes
        : maxDiaGlobal;
    final maxDia =
        widget.aplicarFiltroDiaDoMes ? diaLimiteFiltro : maxDiaGlobal;
    final maxCumulativo = series.fold<double>(0.0, (acc, serie) {
      for (final ponto in serie.pontos) {
        if (ponto.cumulativo > acc) {
          acc = ponto.cumulativo;
        }
      }
      return acc;
    });

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.multiline_chart_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Evolucao despesas no mes',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              widget.categoriaSelecionada == 'Todas'
                  ? 'Acumulado diario de despesas para os ultimos meses.'
                  : 'Acumulado diario de despesas para a categoria ${widget.categoriaSelecionada}.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 10),
            if (series.isEmpty)
              const ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.timeline_outlined),
                title: Text('Sem dados para exibir'),
              )
            else ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (var i = 0; i < series.length; i++)
                    _TrendLegendChip(
                      label: _formatarAnome(series[i].anome),
                      color: _colorForLine(i),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              LayoutBuilder(
                builder: (context, constraints) {
                  const chartHeight = 230.0;
                  final contentWidth = math.max(
                    constraints.maxWidth,
                    (maxDia.clamp(1, 31) * 22.0) + 40.0,
                  );
                  final chartSize = Size(contentWidth, chartHeight);
                  final projectedPoints = _projectEvolucaoPoints(
                    series: series,
                    maxDia: maxDia,
                    maxCumulativo: maxCumulativo,
                    size: chartSize,
                  );
                  _ProjectedEvolucaoPoint? selectedProjectedPoint;
                  if (_selecionado != null) {
                    for (final point in projectedPoints) {
                      if (point.anome == _selecionado!.anome &&
                          point.diaMes == _selecionado!.diaMes &&
                          point.cumulativo == _selecionado!.cumulativo) {
                        selectedProjectedPoint = point;
                        break;
                      }
                    }
                  }
                  return SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SizedBox(
                      width: contentWidth,
                      height: chartHeight,
                      child: Stack(
                        clipBehavior: Clip.none,
                        children: [
                          Positioned.fill(
                            child: MouseRegion(
                              opaque: true,
                              onHover: (event) => _atualizarSelecaoPorPosicao(
                                event.localPosition,
                                projectedPoints,
                              ),
                              onExit: (_) {
                                if (_selecionado != null) {
                                  setState(() => _selecionado = null);
                                }
                              },
                              child: GestureDetector(
                                behavior: HitTestBehavior.opaque,
                                onPanDown: (details) =>
                                    _atualizarSelecaoPorPosicao(
                                  details.localPosition,
                                  projectedPoints,
                                ),
                                onPanUpdate: (details) =>
                                    _atualizarSelecaoPorPosicao(
                                  details.localPosition,
                                  projectedPoints,
                                ),
                                onPanEnd: (_) {
                                  if (_selecionado != null) {
                                    setState(() => _selecionado = null);
                                  }
                                },
                                onPanCancel: () {
                                  if (_selecionado != null) {
                                    setState(() => _selecionado = null);
                                  }
                                },
                                child: CustomPaint(
                                  painter: _EvolucaoDespesasMesPainter(
                                    series: series,
                                    maxDia: maxDia,
                                    maxCumulativo: maxCumulativo,
                                    selecionado: _selecionado,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          if (_selecionado != null &&
                              selectedProjectedPoint != null)
                            _EvolucaoPontoTooltip(
                              ponto: selectedProjectedPoint,
                              chartWidth: contentWidth,
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _EvolucaoDespesasMesPainter extends CustomPainter {
  _EvolucaoDespesasMesPainter({
    required this.series,
    required this.maxDia,
    required this.maxCumulativo,
    required this.selecionado,
  });

  final List<_SerieEvolucaoMes> series;
  final int maxDia;
  final double maxCumulativo;
  final _PontoEvolucaoSelecionado? selecionado;

  @override
  void paint(Canvas canvas, Size size) {
    if (series.isEmpty || maxDia <= 0) return;
    final projectedPoints = _projectEvolucaoPoints(
      series: series,
      maxDia: maxDia,
      maxCumulativo: maxCumulativo,
      size: size,
    );
    if (projectedPoints.isEmpty) return;
    final groupedPoints = <int, List<_ProjectedEvolucaoPoint>>{};
    for (final point in projectedPoints) {
      groupedPoints
          .putIfAbsent(point.anome, () => <_ProjectedEvolucaoPoint>[])
          .add(point);
    }

    final plotWidth = size.width - _evolucaoLeftPadding - _evolucaoRightPadding;
    final plotHeight =
        size.height - _evolucaoTopPadding - _evolucaoBottomPadding;
    final baseY = size.height - _evolucaoBottomPadding;

    final gridPaint = Paint()
      ..color = Colors.black.withValues(alpha: 0.08)
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      final y = _evolucaoTopPadding + (plotHeight * (i / 4));
      canvas.drawLine(Offset(_evolucaoLeftPadding, y),
          Offset(size.width - _evolucaoRightPadding, y), gridPaint);
    }

    for (final entry in groupedPoints.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key))) {
      final pontosProjetados = entry.value
        ..sort((a, b) => a.diaMes.compareTo(b.diaMes));
      final color = pontosProjetados.first.color;
      final pontos = pontosProjetados.map((e) => e.offset).toList();
      if (pontos.isEmpty) continue;

      final linePaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round;

      if (pontos.length > 1) {
        final path = Path()..moveTo(pontos.first.dx, pontos.first.dy);
        for (var i = 1; i < pontos.length; i++) {
          path.lineTo(pontos[i].dx, pontos[i].dy);
        }
        canvas.drawPath(path, linePaint);
      }

      final pointPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;
      for (final point in pontos) {
        canvas.drawCircle(point, 2.8, pointPaint);
      }

      for (final ponto in pontosProjetados) {
        final isSelected = selecionado != null &&
            selecionado!.anome == ponto.anome &&
            selecionado!.diaMes == ponto.diaMes &&
            selecionado!.cumulativo == ponto.cumulativo;
        if (!isSelected) {
          continue;
        }
        final stroke = Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5;
        canvas.drawCircle(ponto.offset, 6.0, stroke);
        canvas.drawCircle(ponto.offset, 3.2, pointPaint);
      }
    }

    final eixoDias = _buildEixoDias(maxDia);
    final stepX = maxDia == 1 ? 0.0 : plotWidth / (maxDia - 1);
    for (final dia
        in eixoDias.where((value) => value >= 1 && value <= maxDia)) {
      final x = _evolucaoLeftPadding + ((dia - 1) * stepX);
      final label = TextPainter(
        text: TextSpan(
          text: dia.toString(),
          style: const TextStyle(
              fontSize: 10,
              color: Color(0xFF64748B),
              fontWeight: FontWeight.w600),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      label.paint(
          canvas,
          Offset(
              x - (label.width / 2), size.height - _evolucaoBottomPadding + 6));
    }
  }

  @override
  bool shouldRepaint(covariant _EvolucaoDespesasMesPainter oldDelegate) {
    if (oldDelegate.maxDia != maxDia ||
        oldDelegate.maxCumulativo != maxCumulativo ||
        oldDelegate.selecionado != selecionado) {
      return true;
    }
    if (oldDelegate.series.length != series.length) {
      return true;
    }
    for (var i = 0; i < series.length; i++) {
      final atual = series[i];
      final antigo = oldDelegate.series[i];
      if (atual.anome != antigo.anome ||
          atual.pontos.length != antigo.pontos.length) {
        return true;
      }
      for (var j = 0; j < atual.pontos.length; j++) {
        final pontoAtual = atual.pontos[j];
        final pontoAntigo = antigo.pontos[j];
        if (pontoAtual.diaMes != pontoAntigo.diaMes ||
            pontoAtual.cumulativo != pontoAntigo.cumulativo) {
          return true;
        }
      }
    }
    return false;
  }
}

class _EvolucaoPontoTooltip extends StatelessWidget {
  const _EvolucaoPontoTooltip({
    required this.ponto,
    required this.chartWidth,
  });

  final _ProjectedEvolucaoPoint ponto;
  final double chartWidth;

  @override
  Widget build(BuildContext context) {
    const tooltipWidth = 170.0;
    const tooltipHeight = 88.0;
    final maxLeft = math.max(6.0, chartWidth - tooltipWidth - 6.0);
    final left = (ponto.offset.dx - (tooltipWidth / 2)).clamp(6.0, maxLeft);
    const maxTop = 230.0 - tooltipHeight - 10;
    final top = (ponto.offset.dy - tooltipHeight - 12).clamp(6.0, maxTop);

    return Positioned(
      left: left,
      top: top,
      child: IgnorePointer(
        child: Container(
          width: tooltipWidth,
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A).withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            boxShadow: const [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 8,
                offset: Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Dia ${ponto.diaMes}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  fontSize: 15,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Mês/ano: ${_formatarAnome(ponto.anome)}',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.86),
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Valor acumulado: ${formatarMoeda(ponto.cumulativo)}',
                style: TextStyle(
                  color: ponto.color,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

const double _evolucaoLeftPadding = 20.0;
const double _evolucaoRightPadding = 14.0;
const double _evolucaoTopPadding = 12.0;
const double _evolucaoBottomPadding = 26.0;

List<_ProjectedEvolucaoPoint> _projectEvolucaoPoints({
  required List<_SerieEvolucaoMes> series,
  required int maxDia,
  required double maxCumulativo,
  required Size size,
}) {
  if (series.isEmpty || maxDia <= 0) {
    return const <_ProjectedEvolucaoPoint>[];
  }
  final plotWidth = size.width - _evolucaoLeftPadding - _evolucaoRightPadding;
  final plotHeight = size.height - _evolucaoTopPadding - _evolucaoBottomPadding;
  if (plotWidth <= 0 || plotHeight <= 0) {
    return const <_ProjectedEvolucaoPoint>[];
  }

  final safeMax = maxCumulativo > 0 ? maxCumulativo : 1.0;
  final stepX = maxDia == 1 ? 0.0 : plotWidth / (maxDia - 1);
  final baseY = size.height - _evolucaoBottomPadding;
  final points = <_ProjectedEvolucaoPoint>[];

  for (var index = 0; index < series.length; index++) {
    final serie = series[index];
    final color = _colorForLine(index);
    for (final ponto in serie.pontos) {
      if (ponto.diaMes < 1 || ponto.diaMes > maxDia) {
        continue;
      }
      final diaNormalizado = ponto.diaMes;
      final x = _evolucaoLeftPadding + ((diaNormalizado - 1) * stepX);
      final normalized = (ponto.cumulativo / safeMax).clamp(0.0, 1.0);
      final y = baseY - (normalized * plotHeight);
      points.add(
        _ProjectedEvolucaoPoint(
          anome: ponto.anome,
          diaMes: ponto.diaMes,
          cumulativo: ponto.cumulativo,
          color: color,
          offset: Offset(x, y),
        ),
      );
    }
  }

  return points;
}

_ProjectedEvolucaoPoint? _findNearestPoint(
  Offset tap,
  List<_ProjectedEvolucaoPoint> points, {
  required double maxDistance,
}) {
  if (points.isEmpty) {
    return null;
  }
  final maxDistanceSquared = maxDistance * maxDistance;
  _ProjectedEvolucaoPoint? winner;
  double bestDistanceSquared = double.infinity;
  for (final point in points) {
    final dx = tap.dx - point.offset.dx;
    final dy = tap.dy - point.offset.dy;
    final d2 = (dx * dx) + (dy * dy);
    if (d2 <= maxDistanceSquared && d2 < bestDistanceSquared) {
      bestDistanceSquared = d2;
      winner = point;
    }
  }
  return winner;
}

List<int> _buildEixoDias(int maxDia) {
  if (maxDia <= 1) {
    return const <int>[1];
  }
  final intervalo = maxDia <= 8
      ? 1
      : maxDia <= 16
          ? 2
          : maxDia <= 24
              ? 3
              : 5;
  final dias = <int>[1];
  var atual = 1 + intervalo;
  while (atual < maxDia) {
    dias.add(atual);
    atual += intervalo;
  }
  if (!dias.contains(maxDia)) {
    dias.add(maxDia);
  }
  return dias;
}

class _EvolucaoCategoriaCard extends StatelessWidget {
  const _EvolucaoCategoriaCard({
    required this.mesesVisiveis,
    required this.evolucao,
  });

  final List<int> mesesVisiveis;
  final List<_SerieMensal> evolucao;

  @override
  Widget build(BuildContext context) {
    final maxValor = evolucao.isEmpty
        ? 0.0
        : evolucao.map((e) => e.valor).reduce((a, b) => a > b ? a : b);

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
                subtitle: Text(
                    'O gráfico usa o recorte do mês selecionado e o histórico visível.'),
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
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
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
                                      : (108 * (item.valor / maxValor))
                                          .clamp(8, 108)
                                          .toDouble(),
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
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
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
    required this.despesas,
    required this.receitas,
  });

  final List<int> mesesVisiveis;
  final List<_SerieMensal> despesas;
  final List<_SerieMensal> receitas;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final meses = mesesVisiveis.isNotEmpty
        ? mesesVisiveis
        : <int>{
            ...despesas.map((item) => item.anome),
            ...receitas.map((item) => item.anome),
          }.toList()
      ..sort();
    final despesasPorMes = {
      for (final item in despesas) item.anome: item.valor,
    };
    final receitasPorMes = {
      for (final item in receitas) item.anome: item.valor,
    };
    final maxValor = [
      ...despesas.map((item) => item.valor),
      ...receitas.map((item) => item.valor),
    ].fold<double>(0.0, (acc, value) => value > acc ? value : acc);

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
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Período: ${meses.length} meses',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 10),
            const Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _TrendLegendChip(label: 'Despesas', color: Color(0xFFB76E00)),
                _TrendLegendChip(label: 'Receitas', color: Color(0xFF0E7A6D)),
              ],
            ),
            const SizedBox(height: 12),
            if (meses.isEmpty || (despesas.isEmpty && receitas.isEmpty))
              const ListTile(
                leading: Icon(Icons.timeline_outlined),
                title: Text('Sem dados no período escolhido'),
              )
            else
              LayoutBuilder(
                builder: (context, constraints) {
                  final contentWidth =
                      math.max(constraints.maxWidth, meses.length * 80.0);
                  final serieDespesas = meses
                      .map((anome) => despesasPorMes[anome] ?? 0.0)
                      .toList();
                  final serieReceitas = meses
                      .map((anome) => receitasPorMes[anome] ?? 0.0)
                      .toList();
                  return SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SizedBox(
                      width: contentWidth,
                      height: 224,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          SizedBox(
                            height: 164,
                            child: CustomPaint(
                              painter: _TrendLinesPainter(
                                despesas: serieDespesas,
                                receitas: serieReceitas,
                                maxValue: maxValor,
                                despesaColor: const Color(0xFFB76E00),
                                receitaColor: const Color(0xFF0E7A6D),
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: meses
                                .map(
                                  (anome) => Expanded(
                                    child: FittedBox(
                                      fit: BoxFit.scaleDown,
                                      child: Text(
                                        _formatarAnome(anome),
                                        textAlign: TextAlign.center,
                                        maxLines: 1,
                                        style: theme.textTheme.bodySmall,
                                      ),
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}

class _TrendLegendChip extends StatelessWidget {
  const _TrendLegendChip({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
          ),
        ],
      ),
    );
  }
}

class _TrendLinesPainter extends CustomPainter {
  _TrendLinesPainter({
    required this.despesas,
    required this.receitas,
    required this.maxValue,
    required this.despesaColor,
    required this.receitaColor,
  });

  final List<double> despesas;
  final List<double> receitas;
  final double maxValue;
  final Color despesaColor;
  final Color receitaColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (despesas.isEmpty || receitas.isEmpty) return;

    const leftPadding = 12.0;
    const rightPadding = 12.0;
    const topPadding = 12.0;
    const bottomPadding = 12.0;
    final plotWidth = size.width - leftPadding - rightPadding;
    final plotHeight = size.height - topPadding - bottomPadding;
    final seriesLength = math.max(despesas.length, receitas.length);
    if (seriesLength <= 0 || plotWidth <= 0 || plotHeight <= 0) return;

    final safeMax = maxValue > 0 ? maxValue : 1.0;
    final stepX = seriesLength == 1 ? 0.0 : plotWidth / (seriesLength - 1);
    final baseY = size.height - bottomPadding;

    final gridPaint = Paint()
      ..color = Colors.black.withValues(alpha: 0.08)
      ..strokeWidth = 1;
    for (var i = 0; i <= 3; i++) {
      final y = topPadding + (plotHeight * (i / 3));
      canvas.drawLine(Offset(leftPadding, y),
          Offset(size.width - rightPadding, y), gridPaint);
    }

    void drawSeries(List<double> values, Color color) {
      final points = <Offset>[];
      for (var i = 0; i < values.length; i++) {
        final x = leftPadding + (stepX * i);
        final normalized = (values[i] / safeMax).clamp(0.0, 1.0);
        final y = baseY - (normalized * plotHeight);
        points.add(Offset(x, y));
      }

      if (points.isEmpty) return;

      final linePaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round;

      if (points.length > 1) {
        final path = Path()..moveTo(points.first.dx, points.first.dy);
        for (var i = 1; i < points.length; i++) {
          path.lineTo(points[i].dx, points[i].dy);
        }
        canvas.drawPath(path, linePaint);
      }

      final pointPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;
      for (final point in points) {
        canvas.drawCircle(point, 3.5, pointPaint);
      }

      for (var i = 0; i < points.length; i++) {
        final textPainter = TextPainter(
          text: TextSpan(
            text: _formatCompact(values[i]),
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
          textDirection: TextDirection.ltr,
          maxLines: 1,
        )..layout();
        final dx = points[i].dx - (textPainter.width / 2);
        final dy =
            (points[i].dy - textPainter.height - 6).clamp(0.0, size.height);
        textPainter.paint(canvas, Offset(dx, dy));
      }
    }

    drawSeries(despesas, despesaColor);
    drawSeries(receitas, receitaColor);
  }

  @override
  bool shouldRepaint(covariant _TrendLinesPainter oldDelegate) {
    return oldDelegate.maxValue != maxValue ||
        oldDelegate.despesaColor != despesaColor ||
        oldDelegate.receitaColor != receitaColor ||
        oldDelegate.despesas.length != despesas.length ||
        oldDelegate.receitas.length != receitas.length ||
        !_sameValues(oldDelegate.despesas, despesas) ||
        !_sameValues(oldDelegate.receitas, receitas);
  }

  bool _sameValues(List<double> a, List<double> b) {
    if (a.length != b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }

  String _formatCompact(double value) {
    final absValue = value.abs();
    if (absValue >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1).replaceAll('.', ',')}M';
    }
    if (absValue >= 1000) {
      return '${(value / 1000).toStringAsFixed(1).replaceAll('.', ',')}k';
    }
    return value.toStringAsFixed(0).replaceAll('.', ',');
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
                  child: Icon(semanticState.icon,
                      color: semanticState.foreground, size: 18),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: theme.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.w800),
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
                  Icon(semanticState.icon,
                      size: 18, color: semanticState.foreground),
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
                    color: isOnline
                        ? const Color(0xFF7CF2C8)
                        : const Color(0xFFF7C46C),
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

Color _colorForLine(int index) {
  const palette = <Color>[
    Color(0xFF0E7A6D),
    Color(0xFF2563EB),
    Color(0xFFB76E00),
    Color(0xFF9333EA),
    Color(0xFFDC2626),
  ];
  if (palette.isEmpty) return const Color(0xFF0E7A6D);
  return palette[index % palette.length];
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

class _EvolucaoDespesaDia {
  _EvolucaoDespesaDia({
    required this.anome,
    required this.diaMes,
    required this.cumulativo,
  });

  final int anome;
  final int diaMes;
  final double cumulativo;
}

class _SerieEvolucaoMes {
  _SerieEvolucaoMes({
    required this.anome,
    required this.pontos,
  });

  final int anome;
  final List<_EvolucaoDespesaDia> pontos;
}

class _ProjectedEvolucaoPoint {
  _ProjectedEvolucaoPoint({
    required this.anome,
    required this.diaMes,
    required this.cumulativo,
    required this.color,
    required this.offset,
  });

  final int anome;
  final int diaMes;
  final double cumulativo;
  final Color color;
  final Offset offset;
}

class _PontoEvolucaoSelecionado {
  const _PontoEvolucaoSelecionado({
    required this.anome,
    required this.diaMes,
    required this.cumulativo,
    required this.color,
  });

  final int anome;
  final int diaMes;
  final double cumulativo;
  final Color color;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) {
      return true;
    }
    return other is _PontoEvolucaoSelecionado &&
        other.anome == anome &&
        other.diaMes == diaMes &&
        other.cumulativo == cumulativo &&
        other.color == color;
  }

  @override
  int get hashCode => Object.hash(anome, diaMes, cumulativo, color);
}

