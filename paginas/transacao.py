"""
Página de Transações.
Gerencia adição de receitas, despesas, transferências e investimentos.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

from src.config import CONTAS, CONTAS_INVEST, CATEGORIAS_DESPESA, CATEGORIAS_RECEITA, CATEGORIAS_INVESTIMENTO
from src.services.data_handler import salvar_transacao
from src.services.google_sheets import get_sheet
from src.analytics.calculations import calcular_saldo


def verificar_duplicata(df, valor, conta, data):
    """Verifica se existe transação com mesmo valor, conta e data."""
    data_str = data.strftime('%d/%m/%Y %H:%M')
    return df[(df['Valor'] == valor) & (df['Conta'] == conta) & (df['Data'] == data_str)]


def adicionar_receita(df, path: str = '.'):
    """Formulário para adicionar uma receita."""
    placeholder = st.empty()
    with placeholder.container():
        id = df['id'].max() + 1
        nome = st.text_input('Nome')
        obs = st.text_input('Comentário')
        tipo = "Receita"
        valor = st.number_input("Valor")
        categoria = st.selectbox("Tipo da Receita", CATEGORIAS_RECEITA)
        conta = st.selectbox("Conta", CONTAS)
        data = st.date_input("Data")
        tag = st.multiselect("TAG", df['TAG'].dropna().drop_duplicates().tolist())
        desconsiderar = st.checkbox('Desconsiderar na análise')

    if st.button("Salvar"):
        duplicatas = verificar_duplicata(df, valor, conta, datetime.combine(data, datetime.min.time()))
        if not duplicatas.empty:
            st.warning("⚠️ Transação similar encontrada!")
            st.write("**Detalhes da transação existente:**")
            existente = duplicatas.iloc[0]
            st.write(f"- Nome: {existente['Nome']}")
            st.write(f"- Tipo: {existente['Tipo']}")
            st.write(f"- Categoria: {existente['Categoria']}")
            st.write(f"- Valor: R$ {existente['Valor']:.2f}")
            st.write(f"- Conta: {existente['Conta']}")
            st.write(f"- Data: {existente['Data'].strftime('%d/%m/%Y')}")
            if existente['Obs']:
                st.write(f"- Observação: {existente['Obs']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirmar (adicionar mesmo assim)"):
                    sheet = get_sheet(path)
                    df_atualizado = salvar_transacao(
                        sheet, df, id, nome, tipo, valor, categoria, conta, 
                        datetime.combine(data, datetime.min.time()), obs, tag,
                        desconsiderar=desconsiderar
                    )
                    st.session_state.df = df_atualizado
                    placeholder.empty()
                    st.success("Transação adicionada com sucesso!")
                    st.rerun()
            with col2:
                if st.button("❌ Ignorar"):
                    st.info("Transação ignorada. Você pode ajustar os dados e tentar novamente.")
        else:
            sheet = get_sheet(path)
            df_atualizado = salvar_transacao(
                sheet, df, id, nome, tipo, valor, categoria, conta, 
                datetime.combine(data, datetime.min.time()), obs, tag,
                desconsiderar=desconsiderar
            )
            st.session_state.df = df_atualizado
            placeholder.empty()
            placeholder = st.empty()
            with placeholder.container():
                if not st.button('ok'):
                    st.stop()


def adicionar_despesa(df, last_date, last_account, path: str = '.'):
    """Formulário para adicionar uma despesa."""
    placeholder = st.empty()
    with placeholder.container():
        id = df['id'].max() + 1
        nome = st.text_input('Nome')
        obs = st.text_input('Comentário')
        tag = st.multiselect("TAG", df['TAG'].dropna().drop_duplicates().tolist())
        tipo = "Despesa"
        valor = -st.number_input("Valor")

        col1, col2 = st.columns([3, 1])
        with col1:
            parcelado = st.checkbox('Compra parcelada?')
        with col2:
            if parcelado:
                parcelas = st.number_input('Quantas Parcelas?', min_value=1, step=1)
            else:
                parcelas = None

        categoria = st.selectbox("Tipo da despesa", CATEGORIAS_DESPESA)

        if last_account in CONTAS:
            conta = st.selectbox("Conta", CONTAS, CONTAS.index(last_account))
        else:
            conta = st.selectbox("Conta", CONTAS)
        
        data = st.date_input("Data")
        desconsiderar = st.checkbox('Desconsiderar na análise')

    if st.button("Salvar"):
        duplicatas = verificar_duplicata(df, valor, conta, datetime.combine(data, datetime.min.time()))
        if not duplicatas.empty:
            st.warning("⚠️ Transação similar encontrada!")
            st.write("**Detalhes da transação existente:**")
            existente = duplicatas.iloc[0]
            st.write(f"- Nome: {existente['Nome']}")
            st.write(f"- Tipo: {existente['Tipo']}")
            st.write(f"- Categoria: {existente['Categoria']}")
            st.write(f"- Valor: R$ {existente['Valor']:.2f}")
            st.write(f"- Conta: {existente['Conta']}")
            st.write(f"- Data: {existente['Data'].strftime('%d/%m/%Y')}")
            if existente['Obs']:
                st.write(f"- Observação: {existente['Obs']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirmar (adicionar mesmo assim)"):
                    sheet = get_sheet(path)
                    df_atualizado = salvar_transacao(
                        sheet, df, id, nome, tipo, valor, categoria, conta,
                        datetime.combine(data, datetime.min.time()), obs, tag,
                        parcelas=parcelas, desconsiderar=desconsiderar
                    )
                    st.session_state.df = df_atualizado
                    placeholder.empty()
                    st.success("Transação adicionada com sucesso!")
                    st.rerun()
            with col2:
                if st.button("❌ Ignorar"):
                    st.info("Transação ignorada. Você pode ajustar os dados e tentar novamente.")
        else:
            sheet = get_sheet(path)
            df_atualizado = salvar_transacao(
                sheet, df, id, nome, tipo, valor, categoria, conta,
                datetime.combine(data, datetime.min.time()), obs, tag,
                parcelas=parcelas, desconsiderar=desconsiderar
            )
            st.session_state.df = df_atualizado
            placeholder.empty()
            placeholder = st.empty()
            with placeholder.container():
                if not st.button('ok'):
                    st.stop()


def adicionar_transferencia(df, opcao: str, path: str = '.'):
    """Formulário para adicionar transferência ou investimento."""
    placeholder = st.empty()
    sheet = get_sheet(path)
    
    if opcao == 'Transferência':
        with placeholder.container():
            id = df['id'].max() + 1
            nome = opcao
            obs = st.text_input('Comentário')
            tipo = opcao
            valor = st.number_input("Valor")
            categoria = opcao
            conta_origem = st.selectbox("Conta de origem", CONTAS)
            conta_destino = st.selectbox("Conta de destino", CONTAS)
            data = st.date_input("Data")
            tag = ''

    if opcao == 'Investimento':
        with placeholder.container():
            id = df['id'].max() + 1
            nome = st.selectbox("Tipo transação", ['Aplicação', 'Resgate'])
            obs = st.text_input('Comentário')
            tipo = opcao
            valor = st.number_input("Valor")
            categoria = st.selectbox("Tipo investimento", CATEGORIAS_INVESTIMENTO)
            conta_origem = st.selectbox("Conta de origem", CONTAS + CONTAS_INVEST)
            conta_destino = st.selectbox("Conta de destino", CONTAS_INVEST + CONTAS)
            data = st.date_input("Data")
            tag = ''

    if st.button("Salvar"):
        # Verificar duplicatas para débito
        duplicatas_debito = verificar_duplicata(df, -valor, conta_origem, datetime.combine(data, datetime.min.time()))
        # Verificar duplicatas para crédito
        duplicatas_credito = verificar_duplicata(df, valor, conta_destino, datetime.combine(data, datetime.min.time()))
        
        duplicatas = pd.concat([duplicatas_debito, duplicatas_credito])
        
        if not duplicatas.empty:
            st.warning("⚠️ Transação similar encontrada!")
            st.write("**Detalhes da(s) transação(ões) existente(s):**")
            for idx, existente in duplicatas.iterrows():
                st.write(f"**Transação {idx+1}:**")
                st.write(f"- Nome: {existente['Nome']}")
                st.write(f"- Tipo: {existente['Tipo']}")
                st.write(f"- Categoria: {existente['Categoria']}")
                st.write(f"- Valor: R$ {existente['Valor']:.2f}")
                st.write(f"- Conta: {existente['Conta']}")
                st.write(f"- Data: {existente['Data'].strftime('%d/%m/%Y')}")
                if existente['Obs']:
                    st.write(f"- Observação: {existente['Obs']}")
                st.write("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirmar (adicionar mesmo assim)"):
                    # Débito na conta origem
                    df_atualizado = salvar_transacao(
                        sheet, df, id, nome, tipo, -valor, categoria, conta_origem,
                        datetime.combine(data, datetime.min.time()), tag, obs,
                        adicionar_transferencia=True
                    )
                    # Crédito na conta destino
                    df_atualizado = salvar_transacao(
                        sheet, df_atualizado, id, nome, tipo, valor, categoria, conta_destino,
                        datetime.combine(data, datetime.min.time()), tag, obs,
                        adicionar_transferencia=True
                    )
                    st.session_state.df = df_atualizado
                    placeholder.empty()
                    st.success("Transferência adicionada com sucesso!")
                    st.rerun()
            with col2:
                if st.button("❌ Ignorar"):
                    st.info("Transferência ignorada. Você pode ajustar os dados e tentar novamente.")
        else:
            # Débito na conta origem
            df_atualizado = salvar_transacao(
                sheet, df, id, nome, tipo, -valor, categoria, conta_origem,
                datetime.combine(data, datetime.min.time()), tag, obs,
                adicionar_transferencia=True
            )
            # Crédito na conta destino
            df_atualizado = salvar_transacao(
                sheet, df_atualizado, id, nome, tipo, valor, categoria, conta_destino,
                datetime.combine(data, datetime.min.time()), tag, obs,
                adicionar_transferencia=True
            )
            st.session_state.df = df_atualizado
            placeholder.empty()
            placeholder = st.empty()
            with placeholder.container():
                if not st.button('ok'):
                    st.stop()


def render(df, path: str = '.'):
    """Renderiza a página de transações."""
    st.title("Gerenciador Financeiro 💰")
    
    last_date = df['Data'].iloc[-1]
    last_account = df['Conta'].iloc[-1]
    
    opcao = st.selectbox("Tipo de transação", ["Receita", "Despesa", "Transferência", "Investimento"])
    st.markdown('# ')
    
    if opcao == "Receita":
        adicionar_receita(df, path)
    elif opcao == "Despesa":
        adicionar_despesa(df, last_date, last_account, path)
    else:
        adicionar_transferencia(df, opcao, path)

    # Exibir saldos
    saldo_s = calcular_saldo(df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Itaú CC', saldo_s.get('Itaú CC', 0))
        st.metric('Cartão Filippe', saldo_s.get('Cartão Filippe', 0))
    with col2:
        st.metric('Cartão Bianca', saldo_s.get('Cartão Bianca', 0))
        st.metric('Cartão Nath', saldo_s.get('Cartão Nath', 0))
    with col3:
        st.metric('Inter', saldo_s.get('Inter', 0))
        st.metric('Nubank', saldo_s.get('Nubank', 0))
    with col4:
        st.metric('VA', saldo_s.get('VA', 0))
        st.metric('VR', saldo_s.get('VR', 0))