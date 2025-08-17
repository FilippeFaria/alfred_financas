from doctest import TestResults
import pandas as pd
import plotly.express as px
from datetime import date
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
import numpy as np
import matplotlib.pyplot as plt


color_map = {
    "Supermercado": "#004c9a",   # Dark Blue - Associated with trust and reliability.
    "Restaurante": "#e63946",    # Red - Associated with appetite and excitement.
    "Viagem": "#47a847",         # Green - Associated with growth and relaxation.
    "Transporte": "#ff9000",     # Orange - Associated with energy and enthusiasm.
    "TV,Internet,Telefone": "#9c26b2",   # Purple - Associated with creativity and luxury.
    "Lazer": "#ffd400",          # Yellow - Associated with happiness and optimism.
    "Compras": "#00b0c3",        # Cyan - Associated with clarity and confidence.
    "Educação": "#d82d7f",       # Magenta - Associated with imagination and passion.
    "Multas": "#c21656",         # Dark Pink - Associated with caution and seriousness.
    "Casa": "#795447",           # Brown - Associated with stability and reliability.
    "Serviços": "#a0a0a0",       # Gray - Associated with neutrality and balance.
    "Saúde": "#008877",          # Teal - Associated with healing and calmness.
    "Presentes": "#8bcd48",      # Lime Green - Associated with freshness and joy.
    "Outros": "#5c7682",         # Dark Gray - Associated with neutrality and formality.
    "Onix": "#000080",           # Navy Blue - Associated with professionalism and authority.
    "Salário": "#04d204",        # Bright Green - Associated with abundance and prosperity.
    "Cobrança": "#800000",       # Dark Red - Associated with urgency and attention.
    "Outros": "#c0c0c0",         # Light Gray - Associated with simplicity and balance.
}



def tratar_df(df):
    
    df['Data'] = pd.to_datetime(df['Data'],format='%d/%m/%Y')
    df['anomes'] = [(str(e.year) + str(e.month)) if len(str(e.month)) == 2 else (str(e.year) + '0' +str(e.month)) for e in df['Data']]
    return df


def saldo(df):
    
    df['Data'] = pd.to_datetime(df['Data'],format='%d/%m/%Y')
    today = date.today()
    saldo_s = df[df['Data'].dt.date <= today].groupby('Conta')['Valor'].sum()
    saldo_s = round(saldo_s,2)
    return saldo_s


def anomes(df):
    df['anomes'] = df['Data'].apply(lambda x: f'{x.year}0{x.month}' if x.month < 10 else f'{x.year}{x.month}')
    df['anomes'] = df['anomes'].apply(lambda x: -1 if x == 'nannan' else x)
    #df['anomes'] = df['anomes'].astype(int)
    return df


def despesa_total(df,now,anome):
    df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa')]
    gasto_total = abs(round(df[(df['Data'].dt.month == now.month) & (df['Data'].dt.year == now.year)]['Valor'].sum(),2))
    ultima_data = df[df['Data'].dt.month == now.month]['Data'].dt.day.max()
    gasto_anterior = abs(round(df[(df['Data'].dt.month == now.month - 1)]['Valor'].sum(),2))
    delta = (gasto_total-gasto_anterior)/gasto_anterior
    st.metric(f'Gasto no mês de {now.month}',value=gasto_total,delta=f'{round(delta,2)*100}%',delta_color='inverse')


import streamlit as st
import pandas as pd
import plotly.express as px

def tendencia_mes(df, anome):
    st.markdown('### Evolução despesas no mês')
    st.markdown('# ')

    # Garante que todos os valores de 'anomes' sejam inteiros
    df['anomes'] = df['anomes'].astype(int)
    
    # Ordena e obtém valores únicos
    todos_anomes = sorted(df['anomes'].unique())

    # Garante que `anome` seja inteiro
    anome = int(anome)

    # Filtra os valores menores ou iguais a `anome`
    anomes_filtrados = [x for x in todos_anomes if x <= anome]

    if not anomes_filtrados:
        st.error("Nenhum valor válido encontrado para `anome`.")
        return

    # Pega o maior valor válido dentro da lista filtrada
    anome = max(anomes_filtrados)

    # Obtém o índice de `anome` na lista ordenada
    idx = todos_anomes.index(anome)

    # Define `anomes_inicio`, garantindo que o índice seja válido
    anomes_inicio = todos_anomes[idx - 4] if idx >= 4 else todos_anomes[0]

    # Filtra os dados conforme os critérios
    df_temp = df[(df['desconsiderar'] == False) & 
                 (df['Tipo'] == 'Despesa') & 
                 (df['anomes'] >= anomes_inicio) & 
                 
                 (df['anomes'] <= anome)].copy()

    # Garante que a coluna 'Data' seja datetime e extrai o dia do mês
    df_temp['Data'] = pd.to_datetime(df_temp['Data'])
    df_temp['dia_mes'] = df_temp['Data'].dt.day

    # Calcula os valores cumulativos
    data = abs(df_temp.groupby(['anomes', 'dia_mes'])['Valor'].sum()).reset_index()
    
    for a in todos_anomes:
        if a in data['anomes'].values:
            idxs = data[data['anomes'] == a].index
            data.loc[idxs, 'cumulativo'] = data[data['anomes'] == a]['Valor'].cumsum()

    # # Calcula as médias para os períodos passado e corrente
    # data_passado = data[data['anomes'] < anome].groupby('dia_mes')['cumulativo'].mean().reset_index()
    # data_corrente = data[data['anomes'] == anome].groupby('dia_mes')['cumulativo'].mean().reset_index()

    
    # Plota o gráfico
    fig = px.line(data, x='dia_mes', y='cumulativo', color='anomes', markers=True)
    st.plotly_chart(fig)

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

def receitas_despesas(df, now, contas_invest, anome=None):
    anome = int(anome)
    st.markdown('### Evolução das receitas e despesas no tempo')
    
    forecast_df = forecast(df, anome)
    forecast_data = abs(forecast_df.groupby('Tipo')['Valor'].sum())
    df = df[(df['desconsiderar'] == False) & (df['anomes'].astype(int) <= anome) & (df['Tipo'] != 'Transferência') & (df['Tipo'] != 'Investimento')]
    data = abs(df.groupby(['anomes','Tipo'])['Valor'].sum()).reset_index()
    data['anomes'] = data['anomes'].astype(str)
    data['text'] = data['Valor'].apply(lambda x: f'{round(x/1000,2)}k')
    
    # Slider para controlar quantos meses mostrar
    total_meses = len(data['anomes'].unique())
    meses_mostrar = st.slider('Número de meses para mostrar', min_value=1, max_value=total_meses, value=min(12,total_meses))
    
    meses_unicos = sorted(data['anomes'].unique())[-meses_mostrar:]  # pega últimos N meses
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
        # Tendência
        X = np.arange(len(group)).reshape(-1,1)
        y = group['Valor'].values
        model = LinearRegression().fit(X, y)
        trend = model.predict(X)
        fig.add_trace(go.Scatter(
            x=group['anomes'],
            y=trend,
            mode='lines',
            name=f'Tendência {tipo}',
            line=dict(color='red' if tipo=='Despesa' else 'green', dash='dash'),
        ))
    
    fig.update_layout(
        barmode='group',
        xaxis_type='category',
        xaxis_rangeslider_visible=True  # permite arrastar horizontalmente
    )
    
    st.plotly_chart(fig, use_container_width=True)


def monthly_spending_by_category_pie(df,anome):
    depara_50_30_20 = {
    "Restaurante": "Desejos",
    "Casa": "Necessidades",
    "Viagem": "Desejos",
    "Supermercado": "Necessidades",
    "Transporte": "Necessidades",
    "Compras": "Desejos",
    "Lazer": "Desejos",
    "Educação": "Necessidades",  # ou Necessidades se for obrigatória (ex: faculdade)
    "Presentes": "Desejos",
    "Saúde": "Necessidades",
    "Serviços": "Necessidades",
    "TV,Internet,Telefone": "Necessidades",
    "Outros": "Desejos",  # ou revisar individualmente,
    "Multas": "Desejos"
}

    data = df[(df['desconsiderar'] == False) & (df['anomes'] == anome) & (df['Tipo'] == 'Despesa')]
    data = abs(data.groupby('Categoria')['Valor'].sum())
    data = data.reset_index()
    data['Classificao'] = data['Categoria'].apply(lambda x:depara_50_30_20[x])   
    on = st.toggle("Detalhar categorias")
    coluna = 'Classificao'
    if on: 
        coluna = 'Categoria'
    fig = px.pie(data, values='Valor', color= coluna,names=coluna,color_discrete_map=color_map, hole=0.4)
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig,use_container_width =False)
    st.markdown('''
Proporção ideal:
                - Necessidades: 50%
                - Desejos: 30%
                - Investimento: 20%
                ''')


def categorias(df,anomes):
    df_full = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa')]
    df = df[(df['desconsiderar'] == False) & (df['anomes'] == anomes) & (df['Tipo'] == 'Despesa')]
    df['Valor'] = abs(df['Valor'])
    data = df.groupby('Categoria')['Valor'].sum().reset_index()
    data = data.sort_values('Valor',ascending=False)

    forecast_df = forecast(df_full,anomes).set_index('Categoria')
    fig = px.bar(data,x = 'Categoria',y='Valor',color='Categoria', text_auto='.2s',color_discrete_map=color_map)
    
    
    for c in forecast_df.index:
        fig.add_trace(go.Bar(
            x=[c],
            y=[forecast_df.loc[c,'Valor']],
            marker_color=color_map[c],
            opacity=0.5,
            showlegend=False,
            text=f"{abs(round(forecast_df.loc[c,'Valor'],2))}",
            textposition='auto',
        ))
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(barmode='overlay',xaxis=dict(showticklabels=False))
    st.plotly_chart(fig)


import streamlit as st
import plotly.express as px

def categorias_tempo(df):
    st.markdown('### Evolução de cada categoria no montante de despesas')
    
    df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa')]
    df['Valor'] = abs(df['Valor'])
    data = df.groupby(['anomes','Categoria'])['Valor'].sum().reset_index()
    
    # Slider para controlar quantos meses mostrar
    total_meses = len(data['anomes'].unique())
    meses_mostrar = st.slider('Número de meses para mostrar', min_value=1, max_value=total_meses, value=min(12,total_meses))
    
    meses_unicos = sorted(data['anomes'].unique())[-meses_mostrar:]  # pega últimos N meses
    data = data[data['anomes'].isin(meses_unicos)]
    
    fig = px.bar(
        data,
        x='anomes',
        y='Valor',
        color='Categoria',
        color_discrete_map=color_map
    )
    
    fig.update_xaxes(type='category')
    fig.update_xaxes(categoryorder='category ascending')
    fig.update_layout(xaxis_rangeslider_visible=True)  # habilita o scroll horizontal
    
    st.plotly_chart(fig, use_container_width=True)



def custo_fixo(df,custo_fixo,anome):
    st.markdown('### Custo Fixo ao longo do tempo ')
    anome = int(anome)
    anomeses = df['anomes'].unique()
    custo_fixo_tempo = pd.DataFrame(columns=['Nome','Valor','anomes'])
    row = 0
    for a in anomeses:
        for i in custo_fixo.index:
            conta = custo_fixo.loc[i,'Conta']
            valor = custo_fixo.loc[i,'Valor']
            
            custo_fixo_tempo.loc[row,'Nome'] = custo_fixo.loc[i,'Conta']
            custo_fixo_tempo.loc[row,'Valor'] = custo_fixo.loc[i,'Valor']
            custo_fixo_tempo.loc[row,'anomes'] = a
            row += 1


    df['anomes'] = df['anomes'].astype(int)
    df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa') & (df['Parcela'].isna() == False) & (df['anomes'] >= anome - 2)]
    df['Valor'] = abs(df['Valor'])
    data = df.groupby(['anomes','Nome'])['Valor'].sum().reset_index()
    data = pd.concat([data,custo_fixo_tempo])
    fig = px.bar(data,x = 'anomes',y='Valor',color='Nome',color_discrete_map=color_map)
    fig.update_xaxes(type='category')
    st.plotly_chart(fig)


def evolucao_categoria(df,anome,now):
    anome = int(anome)
    
    st.markdown('### Evolução de uma categoria no tempo')
    df = df[(df['Tipo'] != 'Investimento') & (df['Tipo'] != 'Transferência')]
    lista_categoria = list(df['Categoria'].unique())
    if 'Investimento' in lista_categoria:
        lista_categoria.remove('Investimento')
    
    categoria_escolhida = st.selectbox('Escolha a categoria',[''] + lista_categoria)
    if categoria_escolhida != '':
        df = df[(df['desconsiderar'] == False) & (df['Categoria'] == categoria_escolhida) & (df['anomes'].astype(int) <= anome)]
        
        df['Valor'] = abs(df['Valor'])
        df = df.sort_values(['anomes','Valor'],ascending = True)
        forecast_df = forecast(df,anome)
        
        #forecast_df = forecast_df[forecast_df['Categoria'] == categoria_escolhida]
        df_grouped = df.groupby('anomes')['Valor'].sum().reset_index()
        df_grouped['rolling_mean'] = df_grouped['Valor'].rolling(window=3).mean()
        df_grouped = df_grouped.drop(index=df_grouped.index[-1])
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_bar(
            x=df['anomes'],
            y=df['Valor'],
            name='Valor',
            marker_color=color_map[categoria_escolhida],
            text=df['Valor'],
            textposition='auto',
            secondary_y=False,
            hovertemplate="Valor: %{y}<br>Nome: %{customdata[1]}<br>Conta: %{customdata[2]}<br>Data: %{customdata[3]}",
            customdata=df[["Valor", "Nome", 'Conta','Data']]
            
            
    )
        # Adicionar linha da média móvel
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
        
        # fig.add_bar(
        #     x= [str(int(anome))],
        #     y=[-forecast_df.loc[0,'Valor']],
        #     name='Forecast',
        #     marker_color=color_map[categoria_escolhida],
        #     opacity=0.6,
        #     text=round(forecast_df.loc[0,'Valor'],2),
        #     textposition='outside',
        #     showlegend=True,
        #     secondary_y=True
        # )
        
        fig.update_layout(barmode='stack', margin=dict(
            t=50
        ))
        fig.add_annotation(
        x=[str(int(anome))],
        y=[forecast_df.loc[0,'Valor']],
        text=str(forecast_df.loc[0,'Valor']),
        showarrow=True,
        xshift=210,
    )

        fig.update_yaxes(showgrid=False, secondary_y=True)
        fig.update_yaxes(range=[min(0, -forecast_df.loc[0,'Valor']), max(df['Valor'])], secondary_y=True)
        fig.update_xaxes(type='category')
        st.plotly_chart(fig)

    return df


def forecast(df,anome):
    
    forecast_df = pd.DataFrame(columns=['Valor','Categoria','Tipo','anomes'])
    #anome = int(anome)
    df = df[(df['desconsiderar'] == False) & (df['anomes'].astype(int) <= int(anome))]
    for e in df['Categoria'].unique():
        row = len(forecast_df)
        forecast_df.loc[row,'Tipo'] = df[df['Categoria'] == e]['Tipo'].iloc[0]
        forecast_df.loc[row,'anomes'] = anome
        forecast_df.loc[row,'Categoria'] = e
        forecast_df.loc[row,'Valor'] = df[df['Categoria'] == e].groupby('anomes')['Valor'].sum()[-4:-1].mean()
        print(anome,e)
        print(df[df['Categoria'] == e].groupby('anomes')['Valor'].sum()[-4:-1])
    
    forecast_df_tocsv = forecast_df.copy()
    forecast_df_tocsv['Valor'] = forecast_df_tocsv['Valor'].astype(str).str.replace('.',',')
    #forecast_df_tocsv.to_csv(r"C:\Users\lippe\Documents\Gestão Financeira\forecast_df.csv",sep=';',encoding='iso-8859-1')
    return forecast_df


def extrato(df,anome):
    anomes = st.selectbox('Escolha o anomes para o extrato',df['anomes'].unique(),list(df['anomes'].unique()).index(anome))
    st.markdown('#### Contas bancárias')
    col1,col2,col3,col4 = st.columns(4)
    sector_list = []
    
    with col1:
        PDA = st.checkbox('Black')
        if PDA:
            sector_list.append('Black')
    with col2:
        itau = st.checkbox('Itaú')
        if itau:
            sector_list.append('Itaú')
    with col3:
        nubank = st.checkbox('Nubank')
        if nubank:
            sector_list.append('Nubank')
    with col4:
        C6 = st.checkbox('C6')
        if C6:
            sector_list.append('C6')
    
    col1,col2,col3,col4 = st.columns(4)
    with col1:
        VR = st.checkbox('VR')
        if VR:
            sector_list.append('VR')
    with col2:
        VA = st.checkbox('VA')
        if VA:
            sector_list.append('VA')

    
    st.markdown('#### Investimentos')
    col1,col2,col3,col4 = st.columns(4)
    with col1:
        Ion = st.checkbox('Ion')
        if Ion:
            sector_list.append('Ion')
    with col2:
        C6Invest = st.checkbox('C6Invest')
        if C6Invest:
            sector_list.append('C6Invest')
    with col3:
        Nuinvest = st.checkbox('Nuinvest')
        if Nuinvest:
            sector_list.append('Nuinvest')
    
    with col4:
        Pay = st.checkbox('99Pay')
        if Pay:
            sector_list.append('99Pay')


    parcelados = st.checkbox('Parcelas')
    if parcelados:
        df = df[df['Parcela'].isnull() == False]
    
    if Ion|C6Invest|Nuinvest|Pay:
        data = df[(df['Conta'].isin(sector_list))]

    elif PDA|itau|nubank|C6|VR|VA:
        data = df[(df['anomes'] == anomes) & (df['Conta'].isin(sector_list))]

    else:
        data = df[(df['anomes'] == anomes)]

    st.dataframe(data)


def acumulo_patrimio(df,contas_invest):
    df = df[(df['Tipo'] == 'Investimento') & df['Conta'].isin(contas_invest)]
    data = df.groupby('anomes')['Valor'].sum().reset_index()

    fig = px.bar(data,x = 'anomes',y='Valor')
    fig.update_xaxes(type='category')
    st.plotly_chart(fig)

    
def aplicacoes_resgates(df,contas_invest):
    st.markdown('### Evolução das receitas e despesas no tempo')
    
    df = df[df['Conta'].isin(contas_invest)]
    data = abs(df.groupby(['anomes','Nome'])['Valor'].sum()).reset_index()
    data['anomes'] = data['anomes'].astype(str)
    data['text'] = data['Valor'].apply(lambda x: f'{round(x/1000,2)}k')
    
    
    patrimonio_total = (df.groupby(['anomes'])['Valor'].sum()).reset_index()
    patrimonio_total['patrimonio'] = patrimonio_total['Valor'].cumsum()


    fig = go.Figure()
    fig.add_trace(go.Scatter(
            x=patrimonio_total['anomes'],
            y=patrimonio_total['patrimonio'],
            mode='lines+markers',
            name='Patrimônio',
            yaxis='y2'      
            #textposition='auto',
            #text=group['text'],
        )

    )
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
    

    #fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(barmode='group',yaxis2=dict(title='Moddel Difference',
            overlaying='y',
            side='right'))
    fig.update_xaxes(type='category')
    fig.update_xaxes(categoryorder='category ascending')
    
    st.plotly_chart(fig)

def tendencia_saldo(df,conta,anome):
    st.markdown('### Saldo no mes')
    st.markdown('# ')
    anome = int(anome)
    todos_anomes = list(df['anomes'].astype(int).sort_values().unique())
    idx = todos_anomes.index(anome)
    anomes_inicio = todos_anomes[idx - 4]
    


    df_temp = df.copy()
    df_temp['anomes'] = df_temp['anomes'].astype(int)
    df_temp = df_temp[(df_temp['Conta'] == conta) & (df_temp['anomes'] >= anomes_inicio) & (df_temp['anomes'] <= anome)]
    df_temp['dia_mes'] = df_temp['Data'].dt.day
    
    data = abs(df_temp.groupby(['anomes','dia_mes'])['Valor'].sum()).reset_index()

    for a in data['anomes'].unique():
        idxs = data[data['anomes'] == a].index
        data.loc[idxs,'cumulativo'] = data[data['anomes'] == a]['Valor'].cumsum()

    data_passado = data[data['anomes'] < anome].groupby('dia_mes')['cumulativo'].mean().sort_index().reset_index()
    data_corrente = data[data['anomes'] == anome].groupby('dia_mes')['cumulativo'].mean().sort_index().reset_index()

    #data_geral = data.groupby('dia_mes')['cumulativo'].mean().sort_index().reset_index()

    #data['text'] = data['Valor'].apply(lambda x: f'{round(x/1000,2)}k')
    

    fig = px.line(data, x='dia_mes', y='cumulativo', color='anomes', markers=True)
    st.plotly_chart(fig)
