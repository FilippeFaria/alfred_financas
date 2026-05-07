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

  Future<void> _abrirCadastro() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _CadastroTransacaoSheet(),
    );
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _abrirCadastro,
        icon: const Icon(Icons.add),
        label: const Text('Novo'),
      ),
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
                    subtitle: Text('${item.tipo} | ${item.categoria} | ${item.conta} | ${item.data}'),
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

class _CadastroTransacaoSheet extends ConsumerStatefulWidget {
  const _CadastroTransacaoSheet();

  @override
  ConsumerState<_CadastroTransacaoSheet> createState() => _CadastroTransacaoSheetState();
}

class _CadastroTransacaoSheetState extends ConsumerState<_CadastroTransacaoSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nomeController = TextEditingController();
  final _valorController = TextEditingController();
  final _obsController = TextEditingController();
  final _parcelasController = TextEditingController(text: '2');
  bool _desconsiderar = false;
  bool _isSaving = false;
  DateTime _data = DateTime.now();
  String _tipo = 'Despesa';
  String? _categoria;
  String? _conta;
  String? _contaDestino;
  String? _cartaoSelecionado;
  String? _tipoInvestimentoNome;
  bool _parcelado = false;

  @override
  void dispose() {
    _nomeController.dispose();
    _valorController.dispose();
    _obsController.dispose();
    _parcelasController.dispose();
    super.dispose();
  }

  Future<void> _selecionarData() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _data,
      firstDate: DateTime(2015, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (picked != null) {
      setState(() => _data = picked);
    }
  }

  List<String> _categoriasPorTipo(CadastroTransacaoOptions opcoes) {
    if (_tipo == 'Despesa') {
      return opcoes.categoriasDespesa;
    }
    if (_tipo == 'Receita') {
      return opcoes.categoriasReceita;
    }
    if (_tipo == 'Investimento') {
      return opcoes.categoriasInvestimento;
    }
    if (_tipo == 'Transferência') {
      return const ['Transferência'];
    }
    return const ['Outros'];
  }

  Future<void> _salvar(CadastroTransacaoOptions opcoes) async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    final notifier = ref.read(transactionsNotifierProvider.notifier);
    final valorBruto = double.tryParse(_valorController.text.replaceAll(',', '.')) ?? 0;

    if (valorBruto <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Informe um valor maior que zero.')),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      if (_tipo == 'Transferência' || _tipo == 'Investimento') {
        if (_conta == null || _contaDestino == null || _contaDestino == _conta) {
          throw Exception('Selecione conta origem e destino diferentes.');
        }
        final nome = _tipo == 'Investimento' ? (_tipoInvestimentoNome ?? 'Aplicação') : 'Transferência';
        final categoria = _tipo == 'Transferência' ? 'Transferência' : (_categoria ?? '');
        await notifier.cadastrarTransacao(
          CadastroTransacaoInput(
            nome: nome,
            tipo: _tipo,
            valor: -valorBruto,
            categoria: categoria,
            conta: _conta!,
            data: _data,
            obs: _obsController.text.trim(),
          ),
        );
        await notifier.cadastrarTransacao(
          CadastroTransacaoInput(
            nome: nome,
            tipo: _tipo,
            valor: valorBruto,
            categoria: categoria,
            conta: _contaDestino!,
            data: _data,
            obs: _obsController.text.trim(),
          ),
        );
      } else if (_tipo == 'Pagamento de Cartão') {
        if (_cartaoSelecionado == null) {
          throw Exception('Selecione o cartão.');
        }
        final cartao = _cartaoSelecionado!;
        if (opcoes.cartoesPagamentoTransferencia.contains(cartao)) {
          await notifier.cadastrarTransacao(
            CadastroTransacaoInput(
              nome: 'Pagamento $cartao',
              tipo: 'Transferência',
              valor: -valorBruto,
              categoria: 'Transferência',
              conta: _conta ?? 'Itaú CC',
              data: _data,
              obs: _obsController.text.trim(),
            ),
          );
          await notifier.cadastrarTransacao(
            CadastroTransacaoInput(
              nome: 'Pagamento $cartao',
              tipo: 'Transferência',
              valor: valorBruto,
              categoria: 'Transferência',
              conta: cartao,
              data: _data,
              obs: _obsController.text.trim(),
            ),
          );
        } else {
          await notifier.cadastrarTransacao(
            CadastroTransacaoInput(
              nome: 'Pagamento $cartao',
              tipo: 'Despesa',
              valor: -valorBruto,
              categoria: 'Outros',
              conta: _conta ?? 'Itaú CC',
              data: _data,
              obs: _obsController.text.trim(),
              desconsiderar: true,
            ),
          );
        }
      } else {
        final valorAjustado = _tipo == 'Despesa' ? -valorBruto : valorBruto;
        final parcelas = _tipo == 'Despesa' && _parcelado
            ? int.tryParse(_parcelasController.text.trim())
            : null;
        await notifier.cadastrarTransacao(
          CadastroTransacaoInput(
            nome: _nomeController.text.trim(),
            tipo: _tipo,
            valor: valorAjustado,
            categoria: _categoria ?? '',
            conta: _conta ?? '',
            data: _data,
            obs: _obsController.text.trim(),
            desconsiderar: _desconsiderar,
            parcelas: parcelas,
          ),
        );
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Transação salva com sucesso.')),
        );
        Navigator.of(context).pop();
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Não foi possível salvar: $error')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final notifier = ref.read(transactionsNotifierProvider.notifier);
    final bottom = MediaQuery.of(context).viewInsets.bottom;

    return FutureBuilder<CadastroTransacaoOptions>(
      future: notifier.carregarOpcoesCadastro(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const SizedBox(height: 280, child: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return SizedBox(
            height: 280,
            child: Center(
              child: Text('Falha ao carregar opções: ${snapshot.error}'),
            ),
          );
        }
        final opcoes = snapshot.data!;
        final categorias = _categoriasPorTipo(opcoes);
        _categoria ??= categorias.isNotEmpty ? categorias.first : null;
        _conta ??= opcoes.contas.isNotEmpty ? opcoes.contas.first : null;
        _contaDestino ??= opcoes.contas.length > 1 ? opcoes.contas[1] : _conta;
        _tipoInvestimentoNome ??= 'Aplicação';
        _cartaoSelecionado ??= opcoes.cartoesPagamento.isNotEmpty ? opcoes.cartoesPagamento.first : null;

        return Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + bottom),
          child: SingleChildScrollView(
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Nova transação', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _tipo,
                    decoration: const InputDecoration(labelText: 'Tipo'),
                    items: const [
                      DropdownMenuItem(value: 'Receita', child: Text('Receita')),
                      DropdownMenuItem(value: 'Despesa', child: Text('Despesa')),
                      DropdownMenuItem(value: 'Transferência', child: Text('Transferência')),
                      DropdownMenuItem(value: 'Investimento', child: Text('Investimento')),
                      DropdownMenuItem(value: 'Pagamento de Cartão', child: Text('Pagamento de Cartão')),
                    ],
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() => _tipo = value);
                    },
                  ),
                  const SizedBox(height: 8),
                  if (_tipo != 'Pagamento de Cartão')
                    TextFormField(
                      controller: _nomeController,
                      decoration: const InputDecoration(labelText: 'Descrição'),
                      validator: (value) {
                        if (_tipo == 'Transferência' || _tipo == 'Investimento') {
                          return null;
                        }
                        if (value == null || value.trim().isEmpty) {
                          return 'Informe a descrição.';
                        }
                        return null;
                      },
                    ),
                  if (_tipo == 'Pagamento de Cartão')
                    DropdownButtonFormField<String>(
                      value: _cartaoSelecionado,
                      decoration: const InputDecoration(labelText: 'Cartão'),
                      items: opcoes.cartoesPagamento
                          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                          .toList(),
                      onChanged: (value) => setState(() => _cartaoSelecionado = value),
                    ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _valorController,
                    decoration: const InputDecoration(labelText: 'Valor'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (value) {
                      final parsed = double.tryParse((value ?? '').replaceAll(',', '.'));
                      if (parsed == null || parsed <= 0) {
                        return 'Informe um valor válido.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 8),
                  if (_tipo == 'Investimento')
                    DropdownButtonFormField<String>(
                      value: _tipoInvestimentoNome,
                      decoration: const InputDecoration(labelText: 'Tipo transação'),
                      items: const [
                        DropdownMenuItem(value: 'Aplicação', child: Text('Aplicação')),
                        DropdownMenuItem(value: 'Resgate', child: Text('Resgate')),
                      ],
                      onChanged: (value) => setState(() => _tipoInvestimentoNome = value),
                    ),
                  if (_tipo != 'Pagamento de Cartão')
                    DropdownButtonFormField<String>(
                      value: _categoria,
                      decoration: const InputDecoration(labelText: 'Categoria'),
                      items: categorias.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                      onChanged: (value) => setState(() => _categoria = value),
                    ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    value: _conta,
                    decoration: InputDecoration(
                      labelText: _tipo == 'Transferência' || _tipo == 'Investimento'
                          ? 'Conta origem'
                          : 'Conta',
                    ),
                    items: opcoes.contas.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
                    onChanged: (value) => setState(() => _conta = value),
                  ),
                  if (_tipo == 'Transferência' || _tipo == 'Investimento') ...[
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: _contaDestino,
                      decoration: const InputDecoration(labelText: 'Conta destino'),
                      items: (_tipo == 'Investimento'
                              ? [...opcoes.contas, ...opcoes.contasInvestimento]
                              : opcoes.contas)
                          .toSet()
                          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
                          .toList(),
                      onChanged: (value) => setState(() => _contaDestino = value),
                    ),
                  ],
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _selecionarData,
                    icon: const Icon(Icons.calendar_today_outlined),
                    label: Text('Data: ${_data.toIso8601String().substring(0, 10)}'),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _obsController,
                    decoration: const InputDecoration(labelText: 'Comentário'),
                  ),
                  if (_tipo == 'Despesa') ...[
                    const SizedBox(height: 8),
                    SwitchListTile(
                      value: _desconsiderar,
                      onChanged: (value) => setState(() => _desconsiderar = value),
                      title: const Text('Desconsiderar na análise'),
                    ),
                    SwitchListTile(
                      value: _parcelado,
                      onChanged: (value) => setState(() => _parcelado = value),
                      title: const Text('Compra parcelada'),
                    ),
                    if (_parcelado)
                      TextFormField(
                        controller: _parcelasController,
                        decoration: const InputDecoration(labelText: 'Parcelas'),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (!_parcelado) return null;
                          final n = int.tryParse(value ?? '');
                          if (n == null || n < 1) {
                            return 'Informe quantidade de parcelas.';
                          }
                          return null;
                        },
                      ),
                  ],
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _isSaving ? null : () => _salvar(opcoes),
                      child: Text(_isSaving ? 'Salvando...' : 'Salvar'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
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
              decoration: const InputDecoration(labelText: 'Data inicio (YYYY-MM-DD)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _dataFimController,
              decoration: const InputDecoration(labelText: 'Data fim (YYYY-MM-DD)'),
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
