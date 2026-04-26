"""
Página de Análise.
Gráficos e métricas de despesas, receitas e tendências.
"""
import streamlit as st
from datetime import datetime
import pandas as pd
from src.config import CONTAS_INVEST
from src.services.data_handler import aplicar_filtros
from src.analytics.calculations import adicionar_anomes, exibir_despesa_total
from src.analytics.charts import (
    receitas_despesas,
    tendencia_mes,
    categorias_tempo,
    evolucao_categoria,
    categorias,
    monthly_spending_by_category_pie,
    tendencia_saldo,
)


def render(df, path: str = '.'):
    """Renderiza a página de análise."""
    st.markdown("## Análise Financeira")
    
    # Aplicar filtros
    col1, col2 = st.columns(2)
    with col1:
        desconsiderar = st.checkbox('Desconsiderar grandes transacoes', value=True)
        va = st.checkbox('Desconsiderar VA', value=False)
        vr = st.checkbox('Desconsiderar VR', value=False)
    with col2:
        bianca = st.checkbox('Recorte Bianca', value=False)
        filippe = st.checkbox('Recorte Filippe', value=False)

    df_temp = aplicar_filtros(df, desconsiderar, va, vr, bianca, filippe)
    
    # Filtro de dia do mês
    now = datetime.now()
    if now.month >= 10:
        anome = f'{now.year}{now.month}'
    else:
        anome = f'{now.year}0{now.month}'
    
    day_to_date = st.checkbox('Comparar aos dias do mês')
    if day_to_date:
        df_temp = adicionar_anomes(df_temp)
        data_max = df_temp[(df_temp['anomes'] == anome) & (df_temp['Parcela'].isna())].Data.dt.day.max()
        df_temp = df_temp[df_temp.Data.dt.day <= data_max]
    
    df_temp = adicionar_anomes(df_temp)
    
    # Métricas de despesas
    df_despesa = df_temp[(df_temp['desconsiderar'] == False) & (df_temp['Tipo'] == 'Despesa')]
    exibir_despesa_total(df_despesa, int(anome))
    
    
    st.markdown("---")
    st.markdown("# Análises")

    # Selector de mês
    anomes_disponiveis = sorted(df_temp['anomes'].unique(), key=lambda x: int(x))
    data_escolhida = st.select_slider('Escolha o anomes', options=anomes_disponiveis, value=anome)
    if data_escolhida:
        anome = data_escolhida
    
    
    
    st.markdown(f"### Categorias das despesas - {data_escolhida}" + (" (Real vs Desejado)"))
    categorias(df_temp, anome, path)
    
    # Botão para editar valores desejados
    if 'editando_categorias' not in st.session_state:
        st.session_state.editando_categorias = False
    
    if not st.session_state.editando_categorias:
        if st.button("✏️ Definir valores desejados"):
            st.session_state.editando_categorias = True
            st.rerun()
    
    if st.session_state.editando_categorias:
        with st.expander("Editar valores desejados por categoria", expanded=True):
            df_mes_temp = df_temp[(df_temp['desconsiderar'] == False) & 
                                    (df_temp['anomes'] == anome) & 
                                    (df_temp['Tipo'] == 'Despesa')]
            df_mes_temp = df_mes_temp.copy()
            df_mes_temp['Valor'] = abs(df_mes_temp['Valor'])
            data_temp = df_mes_temp.groupby('Categoria')['Valor'].sum().reset_index()
            valores_reais_temp = dict(zip(data_temp['Categoria'], data_temp['Valor']))
            todas_categorias_temp = sorted(df_temp[(df_temp['desconsiderar'] == False) & 
                                                    (df_temp['Tipo'] == 'Despesa')]['Categoria'].unique())
            
            col_ed1, col_ed2 = st.columns(2)
            valores_input = {}
            
            with col_ed1:
                st.markdown("**Categorias 1-8**")
                for i, cat in enumerate(todas_categorias_temp[:8]):
                    valor_real = valores_reais_temp.get(cat, 0)
                    valor_default = st.session_state.get('valores_desejados', {}).get(cat, valor_real)
                    valores_input[cat] = st.number_input(
                        f"{cat}", min_value=0.0, value=float(valor_default), step=50.0, key=f"cat_input_{cat}"
                    )
            
            with col_ed2:
                st.markdown("**Categorias 9+**")
                for i, cat in enumerate(todas_categorias_temp[8:], start=8):
                    valor_real = valores_reais_temp.get(cat, 0)
                    valor_default = st.session_state.get('valores_desejados', {}).get(cat, valor_real)
                    valores_input[cat] = st.number_input(
                        f"{cat}", min_value=0.0, value=float(valor_default), step=50.0, key=f"cat_input_{cat}"
                    )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar"):
                    st.session_state.valores_desejados = valores_input.copy()
                    st.session_state.editando_categorias = False
                    
                    from src.services.google_sheets import write_valores_desejados
                    
                    now = datetime.now()
                    df_salvar = pd.DataFrame([
                        {'Data': now.strftime('%d/%m/%Y'), 'Categoria': cat, 'Valor': val}
                        for cat, val in valores_input.items()
                    ])
                    write_valores_desejados(path, df_salvar)
                    st.success("Valores salvos no Google Sheets!")
                    st.rerun()
            
            with col_btn2:
                if st.button("❌ Cancelar"):
                    st.session_state.editando_categorias = False
                    st.rerun()


    col1, col2 = st.columns(2)
    with col2:
        df_tendencia = evolucao_categoria(df_temp, int(anome), now)
        monthly_spending_by_category_pie(df_temp, anome)
        categorias_tempo(df_temp)

    with col1:
        tendencia_mes(df_tendencia, int(anome))
        receitas_despesas(df_temp, CONTAS_INVEST, anome=int(anome))
        
    

    
    # with col2:
    #     tendencia_saldo(df_temp, 'Itaú CC', anome)