import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/transactions_repository.dart';

class TransactionsPage extends ConsumerStatefulWidget {
  const TransactionsPage({super.key});

  @override
  ConsumerState<TransactionsPage> createState() => _TransactionsPageState();
}

class _TransactionsPageState extends ConsumerState<TransactionsPage> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    Future<void>.microtask(() => ref.read(transactionsNotifierProvider.notifier).inicializar());
  }

  void _onScroll() {
    if (!_scrollController.hasClients) {
      return;
    }
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 280) {
      ref.read(transactionsNotifierProvider.notifier).carregarMais();
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(transactionsNotifierProvider);
    final notifier = ref.read(transactionsNotifierProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('Extrato de Transacoes')),
      body: RefreshIndicator(
        onRefresh: notifier.recarregar,
        child: ListView(
          controller: _scrollController,
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            _FiltersCard(
              state: state,
              onApply: notifier.atualizarFiltros,
            ),
            const SizedBox(height: 12),
            if (state.isLoading && state.items.isEmpty) ...const [
              _LoadingCard(),
              SizedBox(height: 8),
              _LoadingCard(),
              SizedBox(height: 8),
              _LoadingCard(),
            ] else if (state.errorMessage != null && state.items.isEmpty) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      const Text('Falha ao carregar transacoes.'),
                      const SizedBox(height: 8),
                      Text(state.errorMessage!, textAlign: TextAlign.center),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: notifier.recarregar,
                        child: const Text('Tentar novamente'),
                      ),
                    ],
                  ),
                ),
              ),
            ] else ...[
              _ResumoCard(total: state.total, exibindo: state.items.length),
              const SizedBox(height: 8),
              ...state.items.map(
                (item) => Card(
                  child: ListTile(
                    title: Text(item.nome),
                    subtitle: Text('${item.categoria} | ${item.conta} | ${item.data}'),
                    trailing: Text('R\$ ${item.valor.toStringAsFixed(2)}'),
                  ),
                ),
              ),
              if (state.isLoadingMore)
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                ),
              if (!state.hasMore && state.items.isNotEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  child: Center(child: Text('Fim do extrato')),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _FiltersCard extends StatefulWidget {
  const _FiltersCard({
    required this.state,
    required this.onApply,
  });

  final TransactionsState state;
  final Future<void> Function(TransactionsFilters) onApply;

  @override
  State<_FiltersCard> createState() => _FiltersCardState();
}

class _FiltersCardState extends State<_FiltersCard> {
  late TextEditingController _dataInicioController;
  late TextEditingController _dataFimController;
  String? _categoria;
  String? _conta;
  String? _tipo;

  @override
  void initState() {
    super.initState();
    final filtros = widget.state.filtros;
    _dataInicioController = TextEditingController(text: filtros.dataInicio ?? '');
    _dataFimController = TextEditingController(text: filtros.dataFim ?? '');
    _categoria = filtros.categoria;
    _conta = filtros.conta;
    _tipo = filtros.tipo;
  }

  @override
  void didUpdateWidget(covariant _FiltersCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.state.filtros != widget.state.filtros) {
      _dataInicioController.text = widget.state.filtros.dataInicio ?? '';
      _dataFimController.text = widget.state.filtros.dataFim ?? '';
      _categoria = widget.state.filtros.categoria;
      _conta = widget.state.filtros.conta;
      _tipo = widget.state.filtros.tipo;
    }
  }

  @override
  void dispose() {
    _dataInicioController.dispose();
    _dataFimController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final opcoes = widget.state.opcoes;
    final filtros = widget.state.filtros;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Filtros', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            TextField(
              controller: _dataInicioController,
              decoration: const InputDecoration(
                labelText: 'Data inicio (YYYY-MM-DD)',
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _dataFimController,
              decoration: const InputDecoration(
                labelText: 'Data fim (YYYY-MM-DD)',
              ),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              value: _categoria,
              decoration: const InputDecoration(labelText: 'Categoria'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Todas')),
                ...?opcoes?.categorias.map(
                  (item) => DropdownMenuItem<String?>(value: item, child: Text(item)),
                ),
              ],
              onChanged: (value) => setState(() => _categoria = value),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              value: _conta,
              decoration: const InputDecoration(labelText: 'Conta'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Todas')),
                ...?opcoes?.contas.map(
                  (item) => DropdownMenuItem<String?>(value: item, child: Text(item)),
                ),
              ],
              onChanged: (value) => setState(() => _conta = value),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              value: _tipo,
              decoration: const InputDecoration(labelText: 'Tipo'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Todos')),
                ...?opcoes?.tipos.map(
                  (item) => DropdownMenuItem<String?>(value: item, child: Text(item)),
                ),
              ],
              onChanged: (value) => setState(() => _tipo = value),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () async {
                      _dataInicioController.clear();
                      _dataFimController.clear();
                      setState(() {
                        _categoria = null;
                        _conta = null;
                        _tipo = null;
                      });
                      await widget.onApply(const TransactionsFilters());
                    },
                    child: const Text('Limpar'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilledButton(
                    onPressed: () async {
                      await widget.onApply(
                        filtros.copyWith(
                          dataInicio: _dataInicioController.text.trim().isEmpty
                              ? null
                              : _dataInicioController.text.trim(),
                          dataFim: _dataFimController.text.trim().isEmpty
                              ? null
                              : _dataFimController.text.trim(),
                          categoria: _categoria,
                          conta: _conta,
                          tipo: _tipo,
                          clearDataInicio: _dataInicioController.text.trim().isEmpty,
                          clearDataFim: _dataFimController.text.trim().isEmpty,
                          clearCategoria: _categoria == null,
                          clearConta: _conta == null,
                          clearTipo: _tipo == null,
                        ),
                      );
                    },
                    child: const Text('Aplicar'),
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

class _ResumoCard extends StatelessWidget {
  const _ResumoCard({required this.total, required this.exibindo});

  final int total;
  final int exibindo;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.receipt_long_outlined),
        title: const Text('Resumo do extrato'),
        subtitle: Text('Exibindo $exibindo de $total registros'),
      ),
    );
  }
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 76,
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(12),
      ),
    );
  }
}
