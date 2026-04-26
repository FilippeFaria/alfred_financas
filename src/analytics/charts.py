"""
Gráficos e visualizações com Plotly.
Contém funções de plotting para análise financeira.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime

from src.analytics.calculations import COLOR_MAP, forecast


def tendencia_mes(df: pd.DataFrame, anome: int) -> None:
    """Exibe gráfico de evolução das despesas no mês."""
    st.markdown('### Evolução despesas no mês')
    st.markdown('# ')

    df = df.copy()
    df['anomes'] = df['anomes'].astype(int)
    
    todos_anomes = sorted(df['anomes'].unique())
    anome = int(anome)
    anomes_filtrados = [x for x in todos_anomes if x <= anome]

    if not anomes_filtrados:
        st.error("Nenhum valor válido encontrado para `anome`.")
        return

    anome = max(anomes_filtrados)
    idx = todos_anomes.index(anome)
    anomes_inicio = todos_anomes[idx - 4] if idx >= 4 else todos_anomes[0]

    df_temp = df[(df['desconsiderar'] == False) & 
                 (df['Tipo'] == 'Despesa') & 
                 (df['anomes'] >= anomes_inicio) & 
                 (df['anomes'] <= anome)].copy()

    # Converter apenas para extrair dia (dados já normalizados em '%d/%m/%Y %H:%M')
    df_temp['Data'] = pd.to_datetime(df_temp['Data'], format='%d/%m/%Y %H:%M')
    df_temp['dia_mes'] = df_temp['Data'].dt.day

    data = abs(df_temp.groupby(['anomes', 'dia_mes'])['Valor'].sum()).reset_index()
    
    for a in todos_anomes:
        if a in data['anomes'].values:
            idxs = data[data['anomes'] == a].index
            data.loc[idxs, 'cumulativo'] = data[data['anomes'] == a]['Valor'].cumsum()

    fig = px.line(data, x='dia_mes', y='cumulativo', color='anomes', markers=True)
    st.plotly_chart(fig)


def receitas_despesas(df: pd.DataFrame, contas_invest: list, anome: int) -> None:
    """Exibe gráfico de evolução de receitas e despesas no tempo."""
    anome = int(anome)
    st.markdown('### Evolução das receitas e despesas no tempo')
    
    forecast_df = forecast(df, anome)
    forecast_data = abs(forecast_df.groupby('Tipo')['Valor'].sum())
    
    df = df[(df['desconsiderar'] == False) & 
            (df['anomes'].astype(int) <= anome) & 
            (df['Tipo'] != 'Transferência') & 
            (df['Tipo'] != 'Investimento')]
    
    data = abs(df.groupby(['anomes', 'Tipo'])['Valor'].sum()).reset_index()
    data['anomes'] = data['anomes'].astype(str)
    data['text'] = data['Valor'].apply(lambda x: f'{round(x/1000,2)}k')
    
    total_meses = len(data['anomes'].unique())
    meses_mostrar = st.slider('Número de meses para mostrar', min_value=1, max_value=total_meses, value=min(12, total_meses))
    
    meses_unicos = sorted(data['anomes'].unique())[-meses_mostrar:]
    data = data[data['anomes'].isin(meses_unicos)]
    
    fig = go.Figure()
    for tipo, group in data.groupby('Tipo'):
        fig.add_trace(go.Bar(
            x=group['anomes'],
            y=group['Valor'],
            name=tipo,
            marker_color='red' if tipo == 'Despesa' else 'green',
            textposition='auto',
            text=group['text'],
        ))
        X = np.arange(len(group)).reshape(-1, 1)
        y = group['Valor'].values
        model = LinearRegression().fit(X, y)
        trend = model.predict(X)
        fig.add_trace(go.Scatter(
            x=group['anomes'],
            y=trend,
            mode='lines',
            name=f'Tendência {tipo}',
            line=dict(color='red' if tipo == 'Despesa' else 'green', dash='dash'),
        ))
    
    fig.update_layout(
        barmode='group',
        xaxis_type='category',
        xaxis_rangeslider_visible=True
    )
    
    st.plotly_chart(fig, use_container_width=True)


def monthly_spending_by_category_pie(df: pd.DataFrame, anome: int) -> None:
    """Exibe gráfico de pizza com proporção de despesas por categoria."""
    depara_50_30_20 = {
        "Restaurante": "Desejos",
        "Casa": "Necessidades",
        "Viagem": "Desejos",
        "Supermercado": "Necessidades",
        "Transporte": "Necessidades",
        "Compras": "Desejos",
        "Lazer": "Desejos",
        "Educação": "Necessidades",
        "Presentes": "Desejos",
        "Saúde": "Necessidades",
        "Serviços": "Necessidades",
        "Assinaturas": "Necessidades",
        "Cosméticos": "Desejos",
        "Outros": "Desejos",
        "Multas": "Desejos"
    }

    data = df[(df['desconsiderar'] == False) & (df['anomes'] == anome) & (df['Tipo'] == 'Despesa')]
    data = abs(data.groupby('Categoria')['Valor'].sum())
    data = data.reset_index()
    data['Classificao'] = data['Categoria'].apply(lambda x: depara_50_30_20.get(x, 'Outros'))
    
    on = st.toggle("Detalhar categorias")
    coluna = 'Classificao' if not on else 'Categoria'
    
    fig = px.pie(data, values='Valor', color=coluna, names=coluna, color_discrete_map=COLOR_MAP, hole=0.4)
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig, use_container_width=False)
    st.markdown('''
**Proporção ideal:**
- Necessidades: 50%
- Desejos: 30%
- Investimento: 20%
''')


def categorias(df: pd.DataFrame, anomes: int, path: str = '.') -> None:
    """Exibe gráfico de categorias com valores reais vs desejados."""
    from src.services.google_sheets import read_valores_desejados
    
    if 'valores_desejados' not in st.session_state:
        st.session_state.valores_desejados = {}
    if 'valores_desejados_carregados' not in st.session_state:
        st.session_state.valores_desejados_carregados = False
    
    if not st.session_state.valores_desejados_carregados:
        try:
            df_valores = read_valores_desejados(path)
            if not df_valores.empty and 'Categoria' in df_valores.columns and 'Valor' in df_valores.columns:
                st.session_state.valores_desejados = dict(zip(df_valores['Categoria'], df_valores['Valor']))
            st.session_state.valores_desejados_carregados = True
        except Exception as e:
            st.warning(f"Não foi possível carregar valores do Google Sheets: {e}")
    
    df_full = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa')]
    df_mes = df[(df['desconsiderar'] == False) & (df['anomes'] == anomes) & (df['Tipo'] == 'Despesa')]
    df_mes = df_mes.copy()
    df_mes['Valor'] = abs(df_mes['Valor'])
    data = df_mes.groupby('Categoria')['Valor'].sum().reset_index()
    data = data.sort_values('Valor', ascending=False)
    
    valores_reais = dict(zip(data['Categoria'], data['Valor']))
    todas_categorias = sorted(df_full['Categoria'].unique())
    tem_desejados = bool(st.session_state.valores_desejados)
    
    if tem_desejados:
        df_desejado = pd.DataFrame([
            {'Categoria': cat, 'Valor': val} 
            for cat, val in st.session_state.valores_desejados.items()
        ])
    else:
        df_desejado = data.copy()
    
    fig = go.Figure()
    
    primeiro_real = True
    primeiro_desejado = True
    
    for cat in data['Categoria']:
        valor = data[data['Categoria'] == cat]['Valor'].values[0]
        cor = COLOR_MAP.get(cat, '#cccccc')
        fig.add_trace(go.Bar(
            x=[cat],
            y=[valor],
            name='Real (↑)' if primeiro_real else None,
            marker_color=cor,
            opacity=1.0,
            text=f"R$ {valor:,.0f}",
            textposition='auto',
            showlegend=primeiro_real
        ))
        primeiro_real = False
    
    for cat in df_desejado['Categoria']:
        valor = df_desejado[df_desejado['Categoria'] == cat]['Valor'].values[0]
        cor = COLOR_MAP.get(cat, '#cccccc')
        fig.add_trace(go.Bar(
            x=[cat],
            y=[-valor],
            name='Desejado (↓)' if primeiro_desejado else None,
            marker_color=cor,
            opacity=0.4,
            text=f"R$ {valor:,.0f}",
            textposition='auto',
            showlegend=primeiro_desejado
        ))
        primeiro_desejado = False
    
    fig.update_layout(
        barmode='overlay',
        xaxis_title="Categoria",
        yaxis_title="Valor (R$)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig)
    
    total_real = sum(valores_reais.values())
    total_desejado = sum(st.session_state.valores_desejados.values()) if tem_desejados else total_real
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Real", f"R$ {total_real:,.2f}")
    with col2:
        st.metric("Total Desejado", f"R$ {total_desejado:,.2f}")
    with col3:
        diff = total_desejado - total_real
        st.metric("Diferença", f"R$ {diff:,.2f}", delta=f"{diff:,.2f}", delta_color="inverse" if diff > 0 else "normal")
    
    if tem_desejados:
        if st.button("🗑️ Limpar valores desejados"):
            st.session_state.valores_desejados = {}
            st.rerun()


def categorias_tempo(df: pd.DataFrame) -> None:
    """Exibe gráfico de evolução de cada categoria no tempo."""
    st.markdown('### Evolução de cada categoria no montante de despesas')
    
    df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa')]
    df['Valor'] = abs(df['Valor'])
    data = df.groupby(['anomes', 'Categoria'])['Valor'].sum().reset_index()
    
    total_meses = len(data['anomes'].unique())
    meses_mostrar = st.slider('Número de meses para mostrar', min_value=1, max_value=total_meses, value=min(12, total_meses))
    
    meses_unicos = sorted(data['anomes'].unique())[-meses_mostrar:]
    data = data[data['anomes'].isin(meses_unicos)]
    
    fig = px.bar(
        data,
        x='anomes',
        y='Valor',
        color='Categoria',
        color_discrete_map=COLOR_MAP
    )
    
    fig.update_xaxes(type='category')
    fig.update_xaxes(categoryorder='category ascending')
    fig.update_xaxes(rangeslider_visible=True)
    
    st.plotly_chart(fig, use_container_width=True)


def evolucao_categoria(df: pd.DataFrame, anome: int, now: datetime) -> pd.DataFrame:
    """Exibe gráfico de evolução de uma categoria específica."""
    anome = int(anome)
    
    st.markdown('### Evolução de uma categoria no tempo')
    df = df[(df['Tipo'] != 'Investimento') & (df['Tipo'] != 'Transferência')]
    lista_categoria = list(df['Categoria'].unique())
    if 'Investimento' in lista_categoria:
        lista_categoria.remove('Investimento')
    
    categoria_escolhida = st.selectbox('Escolha a categoria', [''] + lista_categoria)
    
    if categoria_escolhida != '':
        df = df[(df['desconsiderar'] == False) & 
                (df['Categoria'] == categoria_escolhida) & 
                (df['anomes'].astype(int) <= anome)]
        
        df = df.copy()
        df['Valor'] = abs(df['Valor'])
        df = df.sort_values(['anomes', 'Valor'], ascending=True)
        forecast_df = forecast(df, anome)
        
        df_grouped = df.groupby('anomes')['Valor'].sum().reset_index()
        df_grouped['rolling_mean'] = df_grouped['Valor'].rolling(window=3).mean()
        df_grouped = df_grouped.drop(index=df_grouped.index[-1])
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_bar(
            x=df['anomes'],
            y=df['Valor'],
            name='Valor',
            marker_color=COLOR_MAP.get(categoria_escolhida, '#cccccc'),
            text=df['Valor'],
            textposition='auto',
            secondary_y=False,
            customdata=df[["Valor", "Nome", 'Conta', 'Data']]
        )
        fig.update_traces(
            selector=dict(type='bar'),
            hovertemplate='Mês: %{x}<br>Valor: R$ %{customdata[0]:,.2f}<br>Nome: %{customdata[1]}<br>Conta: %{customdata[2]}<br>Data: %{customdata[3]}<extra></extra>'
        )
        
        fig.add_trace(
            go.Scatter(
                x=df_grouped['anomes'],
                y=df_grouped['rolling_mean'],
                mode='lines',
                name='Média Móvel (3 meses)',
                line=dict(color='blue')
            ),
            secondary_y=False
        )
        
        fig.update_layout(barmode='stack', margin=dict(t=50))
        fig.add_annotation(
            x=[str(int(anome))],
            y=[forecast_df.loc[0, 'Valor']],
            text=str(forecast_df.loc[0, 'Valor']),
            showarrow=True,
            xshift=210,
        )

        fig.update_yaxes(showgrid=False, secondary_y=True)
        fig.update_yaxes(range=[min(0, -forecast_df.loc[0, 'Valor']), max(df['Valor'])], secondary_y=True)
        fig.update_xaxes(type='category')
        st.plotly_chart(fig)

    return df


def extrato(df: pd.DataFrame, anome: int) -> pd.DataFrame:
    """Exibe extrato filtrado por mês e contas."""
    anomes_disponiveis = sorted(df['anomes'].unique(), key=lambda x: int(x))
    if anome not in anomes_disponiveis:
        anome = anomes_disponiveis[-1] if anomes_disponiveis else anome
    
    anomes = st.select_slider('Escolha o anomes para o extrato', options=anomes_disponiveis, value=anome)
    
    st.markdown('#### Contas bancárias')
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    sector_list = []
    
    with col1:
        if st.checkbox('Cartão Filippe'):
            sector_list.append('Cartão Filippe')
    with col2:
        if st.checkbox('Itaú CC'):
            sector_list.append('Itaú CC')
    with col3:
        if st.checkbox('Nubank'):
            sector_list.append('Nubank')
    with col4:
        if st.checkbox('Cartão Bianca'):
            sector_list.append('Cartão Bianca')
    with col5:
        if st.checkbox('Cartão Nath'):
            sector_list.append('Cartão Nath')
    with col6:
        if st.checkbox('Inter'):
            sector_list.append('Inter')
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.checkbox('VR'):
            sector_list.append('VR')
    with col2:
        if st.checkbox('VA'):
            sector_list.append('VA')

    st.markdown('#### Investimentos')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.checkbox('Ion'):
            sector_list.append('Ion')
    with col2:
        if st.checkbox('C6Invest'):
            sector_list.append('C6Invest')
    with col3:
        if st.checkbox('Nuinvest'):
            sector_list.append('Nuinvest')
    with col4:
        if st.checkbox('99Pay'):
            sector_list.append('99Pay')

    parcelados = st.checkbox('Parcelas')
    if parcelados:
        df = df[df['Parcela'].isnull() == False]

    invest_selected = any(x in sector_list for x in ['Ion', 'C6Invest', 'Nuinvest', '99Pay'])
    contas_selected = any(x in sector_list for x in ['Cartão Filippe', 'Itaú CC', 'Nubank', 'Cartão Bianca', 'Cartão Nath', 'Inter', 'VR', 'VA'])

    if invest_selected:
        data = df[(df['Conta'].isin(sector_list))]
    elif contas_selected:
        data = df[(df['anomes'] == anomes) & (df['Conta'].isin(sector_list))]
    else:
        data = df[(df['anomes'] == anomes)]

    st.dataframe(data, hide_index=True)
    return data


def aplicacoes_resgates(df: pd.DataFrame, contas_invest: list) -> None:
    """Exibe gráfico de aplicações e resgates de investimentos."""
    st.markdown('### Aplicações e Resgates')
    
    df = df[(df['Conta'].isin(contas_invest)) & (df['Tipo'] == 'Investimento')]
    data = abs(df.groupby(['anomes', 'Nome'])['Valor'].sum()).reset_index()
    data['anomes'] = data['anomes'].astype(str)
    data['text'] = data['Valor'].apply(lambda x: f'{round(x/1000,2)}k')
    
    patrimonio_total = df.groupby(['anomes'])['Valor'].sum().reset_index()
    patrimonio_total['patrimonio'] = patrimonio_total['Valor'].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=patrimonio_total['anomes'],
        y=patrimonio_total['patrimonio'],
        mode='lines+markers',
        name='Patrimônio',
        yaxis='y2'
    ))

    for tipo, group in data.groupby('Nome'):
        fig.add_trace(go.Bar(
            x=group['anomes'],
            y=group['Valor'],
            name=tipo,
            marker_color='red' if tipo == 'Resgate' else 'green',
            textposition='auto',
            text=group['text'],
            yaxis='y1'
        ))

    fig.update_layout(
        barmode='group',
        yaxis2=dict(title='Patrimônio', overlaying='y', side='right')
    )
    fig.update_xaxes(type='category')
    fig.update_xaxes(categoryorder='category ascending')
    
    st.plotly_chart(fig)


def tendencia_saldo(df: pd.DataFrame, conta: str, anome: int) -> None:
    """Exibe gráfico de tendência de saldo por conta."""
    st.markdown('### Saldo no mês')
    st.markdown('# ')
    
    anome = int(anome)
    todos_anomes = list(df['anomes'].astype(int).sort_values().unique())
    idx = todos_anomes.index(anome)
    anomes_inicio = todos_anomes[idx - 4]

    df_temp = df.copy()
    df_temp['anomes'] = df_temp['anomes'].astype(int)
    df_temp = df_temp[(df_temp['Conta'] == conta) & 
                      (df_temp['anomes'] >= anomes_inicio) & 
                      (df_temp['anomes'] <= anome)]
    df_temp['dia_mes'] = df_temp['Data'].dt.day
    
    data = abs(df_temp.groupby(['anomes', 'dia_mes'])['Valor'].sum()).reset_index()

    for a in data['anomes'].unique():
        idxs = data[data['anomes'] == a].index
        data.loc[idxs, 'cumulativo'] = data[data['anomes'] == a]['Valor'].cumsum()

    fig = px.line(data, x='dia_mes', y='cumulativo', color='anomes', markers=True)
    st.plotly_chart(fig)
