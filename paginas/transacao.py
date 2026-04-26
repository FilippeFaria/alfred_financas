"""
Pagina de Transacoes.
Gerencia adicao de receitas, despesas, transferencias e investimentos.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from src.analytics.calculations import calcular_saldo
from src.config import (
    CATEGORIAS_DESPESA,
    CATEGORIAS_INVESTIMENTO,
    CATEGORIAS_RECEITA,
    CONTAS,
    CONTAS_INVEST,
)
from src.services.data_handler import salvar_transacao
from src.services.google_sheets import get_sheet


def verificar_duplicata(df, valor, conta, data):
    """Verifica se existe transacao com mesmo valor, conta e data."""
    data_str = data.strftime("%d/%m/%Y %H:%M")
    return df[(df["Valor"] == valor) & (df["Conta"] == conta) & (df["Data"] == data_str)]


def limpar_estado_transacao():
    """Limpa campos do formulario e estados temporarios da pagina."""
    chaves_formulario = [
        "tipo_transacao",
        "nome_receita",
        "obs_receita",
        "valor_receita",
        "cat_receita",
        "conta_receita",
        "data_receita",
        "tag_receita",
        "desc_receita",
        "nome_despesa",
        "obs_despesa",
        "valor_despesa",
        "cat_despesa",
        "conta_despesa",
        "data_despesa",
        "tag_despesa",
        "desc_despesa",
        "parcelado_despesa",
        "parcelas_despesa",
        "obs_transf",
        "valor_transf",
        "co_transf",
        "cd_transf",
        "data_transf",
        "tipo_inv",
        "obs_inv",
        "valor_inv",
        "cat_inv",
        "co_inv",
        "cd_inv",
        "data_inv",
    ]
    chaves_estado = [
        "duplicata_receita_encontrada",
        "dados_receita_form",
        "duplicata_despesa_encontrada",
        "dados_despesa_form",
        "duplicata_transferencia_encontrada",
        "dados_transferencia_form",
    ]

    for chave in chaves_formulario + chaves_estado:
        if chave in st.session_state:
            del st.session_state[chave]


def preparar_confirmacao_salvamento(mensagem="Dados salvos com sucesso!"):
    """Mostra uma tela de confirmacao apos o salvamento."""
    limpar_estado_transacao()
    st.session_state.confirmacao_salvamento_transacao = mensagem


def finalizar_confirmacao_salvamento():
    """Fecha a tela de confirmacao e volta para o formulario limpo."""
    if "confirmacao_salvamento_transacao" in st.session_state:
        del st.session_state.confirmacao_salvamento_transacao


def adicionar_receita(df, path="."):
    """Formulario para adicionar uma receita."""
    if "duplicata_receita_encontrada" not in st.session_state:
        st.session_state.duplicata_receita_encontrada = False
    if "dados_receita_form" not in st.session_state:
        st.session_state.dados_receita_form = None

    transacao_id = df["id"].max() + 1
    nome = st.text_input("Nome", key="nome_receita")
    obs = st.text_input("Comentário", key="obs_receita")
    tipo = "Receita"
    valor = st.number_input("Valor", key="valor_receita")
    categoria = st.selectbox("Tipo da Receita", CATEGORIAS_RECEITA, key="cat_receita")
    conta = st.selectbox("Conta", CONTAS, key="conta_receita")
    data = st.date_input("Data", key="data_receita")
    tag = st.multiselect("TAG", df["TAG"].dropna().drop_duplicates().tolist(), key="tag_receita")
    desconsiderar = st.checkbox("Desconsiderar na análise", key="desc_receita")

    def salvar_receita_callback():
        duplicatas = verificar_duplicata(df, valor, conta, datetime.combine(data, datetime.min.time()))
        if not duplicatas.empty:
            st.session_state.duplicata_receita_encontrada = True
            st.session_state.dados_receita_form = {
                "id": transacao_id,
                "nome": nome,
                "tipo": tipo,
                "valor": valor,
                "categoria": categoria,
                "conta": conta,
                "data": data,
                "obs": obs,
                "tag": tag,
                "desconsiderar": desconsiderar,
            }
            return

        sheet = get_sheet(path)
        df_atualizado = salvar_transacao(
            sheet,
            df,
            transacao_id,
            nome,
            tipo,
            valor,
            categoria,
            conta,
            datetime.combine(data, datetime.min.time()),
            obs,
            tag,
            desconsiderar=desconsiderar,
        )
        st.session_state.df = df_atualizado
        preparar_confirmacao_salvamento()

    if st.session_state.duplicata_receita_encontrada and st.session_state.dados_receita_form:
        st.warning("⚠️ Transação similar encontrada!")
        st.write("**Detalhes da transação existente:**")
        duplicatas = verificar_duplicata(df, valor, conta, datetime.combine(data, datetime.min.time()))
        if not duplicatas.empty:
            existente = duplicatas.iloc[0]
            st.write(f"- Nome: {existente['Nome']}")
            st.write(f"- Tipo: {existente['Tipo']}")
            st.write(f"- Categoria: {existente['Categoria']}")
            st.write(f"- Valor: R$ {existente['Valor']:.2f}")
            st.write(f"- Conta: {existente['Conta']}")
            data_formatada = (
                existente["Data"][:10]
                if isinstance(existente["Data"], str)
                else existente["Data"].strftime("%d/%m/%Y")
            )
            st.write(f"- Data: {data_formatada}")
            if existente["Obs"]:
                st.write(f"- Observação: {existente['Obs']}")

        def confirmar_receita_callback():
            dados = st.session_state.dados_receita_form
            sheet = get_sheet(path)
            df_atualizado = salvar_transacao(
                sheet,
                df,
                dados["id"],
                dados["nome"],
                dados["tipo"],
                dados["valor"],
                dados["categoria"],
                dados["conta"],
                datetime.combine(dados["data"], datetime.min.time()),
                dados["obs"],
                dados["tag"],
                desconsiderar=dados["desconsiderar"],
            )
            st.session_state.df = df_atualizado
            preparar_confirmacao_salvamento()

        def ignorar_receita_callback():
            st.session_state.duplicata_receita_encontrada = False
            st.session_state.dados_receita_form = None

        col1, col2 = st.columns(2)
        with col1:
            st.button("Confirmar (adicionar mesmo assim)", on_click=confirmar_receita_callback, key="btn_confirmar_receita")
        with col2:
            st.button("Ignorar", on_click=ignorar_receita_callback, key="btn_ignorar_receita")
    else:
        st.button("Salvar", on_click=salvar_receita_callback, key="btn_salvar_receita")


def adicionar_despesa(df, last_date, last_account, path="."):
    """Formulario para adicionar uma despesa."""
    if "duplicata_despesa_encontrada" not in st.session_state:
        st.session_state.duplicata_despesa_encontrada = False
    if "dados_despesa_form" not in st.session_state:
        st.session_state.dados_despesa_form = None

    transacao_id = df["id"].max() + 1
    nome = st.text_input("Nome", key="nome_despesa")
    obs = st.text_input("Comentário", key="obs_despesa")
    tag = st.multiselect("TAG", df["TAG"].dropna().drop_duplicates().tolist(), key="tag_despesa")
    tipo = "Despesa"
    valor = -st.number_input("Valor", key="valor_despesa")

    col1, col2 = st.columns([3, 1])
    with col1:
        parcelado = st.checkbox("Compra parcelada?", key="parcelado_despesa")
    with col2:
        parcelas = st.number_input("Quantas Parcelas?", min_value=1, step=1, key="parcelas_despesa") if parcelado else None

    categoria = st.selectbox("Tipo da despesa", CATEGORIAS_DESPESA, key="cat_despesa")

    if last_account in CONTAS:
        conta = st.selectbox("Conta", CONTAS, CONTAS.index(last_account), key="conta_despesa")
    else:
        conta = st.selectbox("Conta", CONTAS, key="conta_despesa")

    data = st.date_input("Data", key="data_despesa")
    desconsiderar = st.checkbox("Desconsiderar na análise", key="desc_despesa")

    def salvar_despesa_callback():
        duplicatas = verificar_duplicata(df, valor, conta, datetime.combine(data, datetime.min.time()))
        if not duplicatas.empty:
            st.session_state.duplicata_despesa_encontrada = True
            st.session_state.dados_despesa_form = {
                "id": transacao_id,
                "nome": nome,
                "tipo": tipo,
                "valor": valor,
                "categoria": categoria,
                "conta": conta,
                "data": data,
                "obs": obs,
                "tag": tag,
                "parcelas": parcelas,
                "desconsiderar": desconsiderar,
            }
            return

        sheet = get_sheet(path)
        df_atualizado = salvar_transacao(
            sheet,
            df,
            transacao_id,
            nome,
            tipo,
            valor,
            categoria,
            conta,
            datetime.combine(data, datetime.min.time()),
            obs,
            tag,
            parcelas=parcelas,
            desconsiderar=desconsiderar,
        )
        st.session_state.df = df_atualizado
        preparar_confirmacao_salvamento()

    if st.session_state.duplicata_despesa_encontrada and st.session_state.dados_despesa_form:
        st.warning("⚠️ Transação similar encontrada!")
        st.write("**Detalhes da transação existente:**")
        duplicatas = verificar_duplicata(df, valor, conta, datetime.combine(data, datetime.min.time()))
        if not duplicatas.empty:
            existente = duplicatas.iloc[0]
            st.write(f"- Nome: {existente['Nome']}")
            st.write(f"- Tipo: {existente['Tipo']}")
            st.write(f"- Categoria: {existente['Categoria']}")
            st.write(f"- Valor: R$ {existente['Valor']:.2f}")
            st.write(f"- Conta: {existente['Conta']}")
            data_formatada = (
                existente["Data"][:10]
                if isinstance(existente["Data"], str)
                else existente["Data"].strftime("%d/%m/%Y")
            )
            st.write(f"- Data: {data_formatada}")
            if existente["Obs"]:
                st.write(f"- Observação: {existente['Obs']}")

        def confirmar_despesa_callback():
            dados = st.session_state.dados_despesa_form
            sheet = get_sheet(path)
            df_atualizado = salvar_transacao(
                sheet,
                df,
                dados["id"],
                dados["nome"],
                dados["tipo"],
                dados["valor"],
                dados["categoria"],
                dados["conta"],
                datetime.combine(dados["data"], datetime.min.time()),
                dados["obs"],
                dados["tag"],
                parcelas=dados["parcelas"],
                desconsiderar=dados["desconsiderar"],
            )
            st.session_state.df = df_atualizado
            preparar_confirmacao_salvamento()

        def ignorar_despesa_callback():
            st.session_state.duplicata_despesa_encontrada = False
            st.session_state.dados_despesa_form = None

        col1, col2 = st.columns(2)
        with col1:
            st.button("Confirmar (adicionar mesmo assim)", on_click=confirmar_despesa_callback, key="btn_confirmar_despesa")
        with col2:
            st.button("Ignorar", on_click=ignorar_despesa_callback, key="btn_ignorar_despesa")
    else:
        st.button("Salvar", on_click=salvar_despesa_callback, key="btn_salvar_despesa")


def adicionar_transferencia(df, opcao, path="."):
    """Formulario para adicionar transferencia ou investimento."""
    if "duplicata_transferencia_encontrada" not in st.session_state:
        st.session_state.duplicata_transferencia_encontrada = False
    if "dados_transferencia_form" not in st.session_state:
        st.session_state.dados_transferencia_form = None

    sheet = get_sheet(path)
    transacao_id = df["id"].max() + 1

    if opcao == "Transferência":
        nome = opcao
        obs = st.text_input("Comentário", key="obs_transf")
        tipo = opcao
        valor = st.number_input("Valor", key="valor_transf")
        categoria = opcao
        conta_origem = st.selectbox("Conta de origem", CONTAS, key="co_transf")
        conta_destino = st.selectbox("Conta de destino", CONTAS, key="cd_transf")
        data = st.date_input("Data", key="data_transf")
        tag = ""
    else:
        nome = st.selectbox("Tipo transação", ["Aplicação", "Resgate"], key="tipo_inv")
        obs = st.text_input("Comentário", key="obs_inv")
        tipo = opcao
        valor = st.number_input("Valor", key="valor_inv")
        categoria = st.selectbox("Tipo investimento", CATEGORIAS_INVESTIMENTO, key="cat_inv")
        conta_origem = st.selectbox("Conta de origem", CONTAS + CONTAS_INVEST, key="co_inv")
        conta_destino = st.selectbox("Conta de destino", CONTAS_INVEST + CONTAS, key="cd_inv")
        data = st.date_input("Data", key="data_inv")
        tag = ""

    def salvar_transferencia_callback():
        duplicatas_debito = verificar_duplicata(df, -valor, conta_origem, datetime.combine(data, datetime.min.time()))
        duplicatas_credito = verificar_duplicata(df, valor, conta_destino, datetime.combine(data, datetime.min.time()))
        duplicatas = pd.concat([duplicatas_debito, duplicatas_credito])

        if not duplicatas.empty:
            st.session_state.duplicata_transferencia_encontrada = True
            st.session_state.dados_transferencia_form = {
                "id": transacao_id,
                "nome": nome,
                "tipo": tipo,
                "valor": valor,
                "categoria": categoria,
                "conta_origem": conta_origem,
                "conta_destino": conta_destino,
                "data": data,
                "tag": tag,
                "obs": obs,
            }
            return

        df_atualizado = salvar_transacao(
            sheet,
            df,
            transacao_id,
            nome,
            tipo,
            -valor,
            categoria,
            conta_origem,
            datetime.combine(data, datetime.min.time()),
            tag,
            obs,
            adicionar_transferencia=True,
        )
        df_atualizado = salvar_transacao(
            sheet,
            df_atualizado,
            transacao_id,
            nome,
            tipo,
            valor,
            categoria,
            conta_destino,
            datetime.combine(data, datetime.min.time()),
            tag,
            obs,
            adicionar_transferencia=True,
        )
        st.session_state.df = df_atualizado
        preparar_confirmacao_salvamento()

    if st.session_state.duplicata_transferencia_encontrada and st.session_state.dados_transferencia_form:
        st.warning("⚠️ Transação similar encontrada!")
        st.write("**Detalhes da(s) transação(ões) existente(s):**")
        duplicatas_debito = verificar_duplicata(df, -valor, conta_origem, datetime.combine(data, datetime.min.time()))
        duplicatas_credito = verificar_duplicata(df, valor, conta_destino, datetime.combine(data, datetime.min.time()))
        duplicatas = pd.concat([duplicatas_debito, duplicatas_credito])

        for indice, existente in duplicatas.iterrows():
            st.write(f"**Transação {indice + 1}:**")
            st.write(f"- Nome: {existente['Nome']}")
            st.write(f"- Tipo: {existente['Tipo']}")
            st.write(f"- Categoria: {existente['Categoria']}")
            st.write(f"- Valor: R$ {existente['Valor']:.2f}")
            st.write(f"- Conta: {existente['Conta']}")
            data_formatada = (
                existente["Data"][:10]
                if isinstance(existente["Data"], str)
                else existente["Data"].strftime("%d/%m/%Y")
            )
            st.write(f"- Data: {data_formatada}")
            if existente["Obs"]:
                st.write(f"- Observação: {existente['Obs']}")
            st.write("---")

        def confirmar_transferencia_callback():
            dados = st.session_state.dados_transferencia_form
            df_atualizado = salvar_transacao(
                sheet,
                df,
                dados["id"],
                dados["nome"],
                dados["tipo"],
                -dados["valor"],
                dados["categoria"],
                dados["conta_origem"],
                datetime.combine(dados["data"], datetime.min.time()),
                dados["tag"],
                dados["obs"],
                adicionar_transferencia=True,
            )
            df_atualizado = salvar_transacao(
                sheet,
                df_atualizado,
                dados["id"],
                dados["nome"],
                dados["tipo"],
                dados["valor"],
                dados["categoria"],
                dados["conta_destino"],
                datetime.combine(dados["data"], datetime.min.time()),
                dados["tag"],
                dados["obs"],
                adicionar_transferencia=True,
            )
            st.session_state.df = df_atualizado
            preparar_confirmacao_salvamento()

        def ignorar_transferencia_callback():
            st.session_state.duplicata_transferencia_encontrada = False
            st.session_state.dados_transferencia_form = None

        col1, col2 = st.columns(2)
        with col1:
            st.button("Confirmar (adicionar mesmo assim)", on_click=confirmar_transferencia_callback, key="btn_confirmar_transf")
        with col2:
            st.button("Ignorar", on_click=ignorar_transferencia_callback, key="btn_ignorar_transf")
    else:
        st.button("Salvar", on_click=salvar_transferencia_callback, key="btn_salvar_transf")


def render(df, path="."):
    """Renderiza a pagina de transacoes."""
    if st.session_state.get("confirmacao_salvamento_transacao"):
        st.write(st.session_state.confirmacao_salvamento_transacao)
        st.button("OK", on_click=finalizar_confirmacao_salvamento, key="btn_ok_salvamento_transacao")
        return

    st.title("Gerenciador Financeiro 💰")

    last_date = df["Data"].iloc[-1]
    last_account = df["Conta"].iloc[-1]

    opcao = st.selectbox(
        "Tipo de transação",
        ["Receita", "Despesa", "Transferência", "Investimento"],
        key="tipo_transacao",
    )
    st.markdown("# ")

    if opcao == "Receita":
        adicionar_receita(df, path)
    elif opcao == "Despesa":
        adicionar_despesa(df, last_date, last_account, path)
    else:
        adicionar_transferencia(df, opcao, path)

    saldo_s = calcular_saldo(df)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Itaú CC", saldo_s.get("Itaú CC", 0))
        st.metric("Cartão Filippe", saldo_s.get("Cartão Filippe", 0))
    with col2:
        st.metric("Cartão Bianca", saldo_s.get("Cartão Bianca", 0))
        st.metric("Cartão Nath", saldo_s.get("Cartão Nath", 0))
    with col3:
        st.metric("Inter", saldo_s.get("Inter", 0))
        st.metric("Nubank", saldo_s.get("Nubank", 0))
    with col4:
        st.metric("VA", saldo_s.get("VA", 0))
        st.metric("VR", saldo_s.get("VR", 0))
