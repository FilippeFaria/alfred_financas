from ssl import Options
import streamlit as st
import pandas as pd
import time
from dateutil.relativedelta import relativedelta
import analytics
from datetime import datetime
import google_sheets

#import gpt_model
st.set_page_config(
layout="wide"
)

path = '.'
#path = r'C:\Users\lippe\OneDrive - Unesp\Documentos\GitHub\alfred_financas'

sheet = google_sheets.get_sheet(path)
contas = ['Itaú','Black','VR','VA','99Pay', 'Nubank','Cartão Nubank','C6','C6 corrente']

contas_invest = ['Ion','Nuinvest','99Pay','C6Invest']

def salvar_dados(id, nome,df, tipo, valor, categoria, conta, data,obs,tag,parcelas=None,desconsiderar=False,adicionar_transferencia=False):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    data_criacao = dt_string

    if parcelas == None:
        # Criando um DataFrame temporário com a nova linha
        nova_linha = pd.DataFrame([{
            'id': id,
            'Nome': nome,
            "Tipo": tipo,
            "Valor": valor,
            "Categoria": categoria,
            "Conta": conta,
            "Data": data.strftime("%Y-%m-%d %H:%M:%S"),
            'Obs': obs,
            'desconsiderar': desconsiderar,
            'Data Criacao': data_criacao,
            'TAG': tag
        }])

        # Concatenando o novo DataFrame ao existente
        df = pd.concat([df, nova_linha], ignore_index=True)
        #st.write(len(df))
        
    else:
        for i in range(0,parcelas):
            # Criando um DataFrame temporário com a nova linha
            nova_linha = pd.DataFrame([{
                'id': id,
                'Nome': nome,
                "Tipo": tipo,
                "Valor": valor,
                "Categoria": categoria,
                "Conta": conta,
                "Data": (data + relativedelta(months=i)).strftime("%Y-%m-%d %H:%M:%S"),
                'Obs': obs,
                'desconsiderar': desconsiderar,
                'Parcela': i + 1,
                "Data origem": data.strftime("%Y-%m-%d %H:%M:%S"),
                'Data Criacao': data_criacao,
                'TAG': tag
            }])

            # Concatenando o novo DataFrame ao existente
            df = pd.concat([df, nova_linha], ignore_index=True)
            st.cache_data.clear()  # Limpa o cache
            st.experimental_rerun()
        st.write('parcelas')
   
    
    # Corrigir o bug da transferencia.
    if (adicionar_transferencia == True) & (valor < 0):
        return df
    else:
        #df['Valor'] =  df['Valor'].astype('str').apply(lambda x:x.replace('.',','))
        df['Data'] = pd.to_datetime(df['Data'],format="%Y-%m-%d %H:%M:%S")
        df['Data'] =  df['Data'].dt.strftime('%d/%m/%Y %H:%M')
        
        google_sheets.write_sheet(sheet, df)
        
        #df.to_csv(fr"{path}/fluxo_de_caixa.csv",sep=';', index=False,encoding='iso-8859-1')
        #df.to_csv(fr"{path}/historico_fluxo/fluxo_de_caixa_{now.day}{now.month}{now.year}.csv",sep=';', index=False,encoding='iso-8859-1')
        
        st.success("Dados salvos com sucesso!")


def adicionar_receita(df):
    placeholder = st.empty()
    with placeholder.container():
        id = df['id'].max() + 1
        nome = st.text_input('Nome')
        obs = st.text_input('Comentário')
        tipo = "Receita"
        valor = st.number_input("Valor")
        categoria = st.selectbox("Tipo da Receita", ["Salário", "Cobrança", "Outros"])
        conta = st.selectbox("Conta", contas)
        data = st.date_input("Data")
        tag = st.multiselect("TAG",df['TAG'].dropna().drop_duplicates())
        
        desconsiderar = st.checkbox('Desconsiderar na análise')
    
    if st.button("Salvar"):
        
        salvar_dados(id,nome,df, tipo, valor, categoria, conta, data,obs,tag,desconsiderar = desconsiderar,)
        placeholder.empty()
        placeholder = st.empty()
        with placeholder.container():
            if not st.button('ok'):
                st.stop()




def adicionar_despesa(df,last_date,last_account):
    placeholder = st.empty()
    with placeholder.container():
        id = df['id'].max() + 1
        nome = st.text_input('Nome')
        obs = st.text_input('Comentário')
        tag = st.multiselect("TAG",df['TAG'].dropna().drop_duplicates())
        tipo = "Despesa"
        valor = -st.number_input("Valor")
    
        col1,col2 = st.columns([3,1])
        with col1:
            parcelado = st.checkbox('Compra parcelada?')
        with col2:
            if parcelado == True:
                parcelas = st.number_input('Quantas Parcelas?',min_value=1,step=1)
            else:
                parcelas = None
                
        
        categoria = st.selectbox("Tipo da despesa", ['Restaurante',"Supermercado",'Viagem',"Transporte", 'TV,Internet,Telefone',"Lazer", 'Compras','Educação',
                                'Multas','Casa','Serviços','Saúde','Presentes', "Outros",'Onix','Investimento'])
        
        if last_account in contas:
            conta = st.selectbox("Conta", contas,contas.index(last_account))
        else:
            conta = st.selectbox("Conta", contas)
        data = st.date_input("Data")
        
        desconsiderar = st.checkbox('Desconsiderar na análise')

    if st.button("Salvar"):
        salvar_dados(id,nome,df, tipo, valor, categoria, conta, data,obs,tag,parcelas=parcelas,desconsiderar=desconsiderar)
        placeholder.empty()
        placeholder = st.empty()
        with placeholder.container():
            if not st.button('ok'):
                st.stop()
        


def adicionar_transferencia(df,opcao):
    placeholder = st.empty()
    if opcao == 'Transferência':
        with placeholder.container():
            id = df['id'].max() + 1
            nome = opcao
            obs = st.text_input('Comentário')
            tipo = opcao
            valor = st.number_input("Valor")
            categoria = opcao
            conta_origem = st.selectbox("Conta de origem", contas)
            conta_destino = st.selectbox("Conta de destino", contas)
            data = st.date_input("Data")
            tag = ''
    if opcao == 'Investimento':
        with placeholder.container():
            id = df['id'].max() + 1
            nome = st.selectbox("Tipo transação", ['Aplicação','Resgate'])
            obs = st.text_input('Comentário')
            tipo = opcao
            valor = st.number_input("Valor")
            categoria = st.selectbox("Tipo investimento", ['Tesouro Selic','CDB','Fundos','LCI','LCA','Ações'])
            conta_origem = st.selectbox("Conta de origem", contas+contas_invest)
            conta_destino = st.selectbox("Conta de destino", contas_invest+contas)
            data = st.date_input("Data")
            tag = ''
        

    if st.button("Salvar"):
        df = salvar_dados(id,nome,df, tipo, -valor, categoria, conta_origem, data,tag,obs,adicionar_transferencia= True)
        salvar_dados(id,nome,df, tipo, valor, categoria, conta_destino, data,tag,obs, adicionar_transferencia = True)
        placeholder.empty()
        placeholder = st.empty()
        with placeholder.container():
            if not st.button('ok'):
                st.stop()
        

def main():
    # Abre o arquivo de prompt do sistema
    # file_path = "C:\\Users\\lippe\\Documents\\Gestão Financeira\\prompt_system.txt"
    # with open(file_path, "r", encoding="utf-8") as file:
    #     prompt_system = file.read()


    df = google_sheets.read_sheet(path)
    df['Valor'] =  df['Valor'].astype('float64')
    df['desconsiderar'] = df['desconsiderar'].replace('TRUE', True).replace('FALSE', False)
    df['Categoria'] = df['Categoria'].str.replace('TV.Internet.Telefone','TV,Internet,Telefone')


    # df = pd.read_csv(fr"{path}/fluxo_de_caixa.csv",encoding='iso-8859-1',sep=';')
    # df['Valor'] =  df['Valor'].astype(str).apply(lambda x:x.replace(',','.')).astype('float64')
    # print('Base Offline lida')
    
    df['Data'] = pd.to_datetime(df['Data'],format="%d/%m/%Y %H:%M")

    last_date = df['Data'].iloc[-1]
    last_account = df['Conta'].iloc[-1]
    
    
    tab1, tab2, tab3,tab4,tab5 = st.tabs(["Transação", "Análise","Alfred","Patrimônio","Extrato",])
    with tab1:
        st.title("Gerenciador Financeiro 💰") 
        opcao = st.selectbox("Tipo de transação", ["Receita", "Despesa", "Transferência","Investimento"])
        st.markdown('#')
        if opcao == "Receita":
            adicionar_receita(df)
        elif opcao == "Despesa":
            adicionar_despesa(df,last_date,last_account)
        else:
            adicionar_transferencia(df,opcao)

        saldo_s = analytics.saldo(df)
        
        col1,col2,col3,col4,col5 = st.columns(5)

        with col1:
            st.metric('Itaú',saldo_s['Itaú'])
        with col2:
            st.metric('Nubank',saldo_s['Nubank'])
        with col3:
            st.metric('Black',saldo_s['Black'])
        with col4:
            st.metric('VR',saldo_s['VR'])
        with col5:
            st.metric('Ion',saldo_s['Ion'])

       
    now = datetime.now()
    df = analytics.anomes(df)

    if now.month >= 10:
        anome = f'{now.year}{now.month}'
    else:
        anome = f'{now.year}0{now.month}'

    with tab2:        
        col1,col2 = st.columns(2)
        with col1:
            desconsiderar = st.checkbox('Desconsiderar grandes transacoes',value =True)
            va = st.checkbox('Desconsiderar VA',value =False)
            vr = st.checkbox('Desconsiderar VR',value =False)

            if desconsiderar:
                grandes_transacoes = [98,99,103,229,245,558,549,701,771,1012,1014,1018,995,978,971,
                                      1081,1050,1326,1733,1663,1744,1756,1766,1867,2327,2350,2327,2625]
                idx = df[df['id'].isin(grandes_transacoes)].index
                df = df.drop(idx)
            if va:
                idx = df[df['Conta'].isin(['VA'])].index
                df = df.drop(idx)

            if vr:
                idx = df[df['Conta'].isin(['VR'])].index
                df = df.drop(idx)
        with col2:
            day_to_date = st.checkbox('Comparar aos dias do mês')
            if day_to_date:
                data_max = df[(df['anomes'] == anome) & (df['Parcela'].isna())].Data.dt.day.max()
                
                df = df[df.Data.dt.day <= data_max]

        analytics.despesa_total(df,now,anome)
        col1, col2 = st.columns(2)
   
        with col2:
            analytics.categorias_tempo(df)
            df_tendencia = analytics.evolucao_categoria(df,anome,now)
        with col1:
            
            analytics.receitas_despesas(df,now,contas_invest,anome=anome) 
            analytics.tendencia_mes(df_tendencia,anome)   
        
        
        col1,col2,col3 = st.columns([2,1,5])
        with col1:
            st.markdown('### Categorias das despesas')
        with col2:
            #st.write(df['anomes'].unique())
            data_escolhida = st.selectbox('Escolha o anomes',df['anomes'].unique(), list(df['anomes'].unique()).index(anome)) 
        col1, col2 = st.columns(2)     
        with col1:            
            if data_escolhida:
                anome = data_escolhida
            
            analytics.categorias(df,anome)                  
        
        with col2:
            
            analytics.monthly_spending_by_category_pie(df,anome)
            analytics.tendencia_saldo(df,'Itaú',anome)
            
            #analytics.custo_fixo(df,custo_fixo,anome)

    with tab3:
        st.write('## Em breve')
        #gpt_model.main_chat(prompt_system,df)


    with tab4:
        col1,col2,col3 = st.columns(3)
        with col2:
            st.metric('Patrimônio Total',saldo_s[contas_invest].sum())
            st.write(saldo_s[contas_invest])
        
        col1,col2,col3,col4 = st.columns(4)
        with col1:
            st.metric('Ion',saldo_s['Ion'])
        with col2:
            st.metric('Nuinvest',saldo_s['Nuinvest'])
        with col3:
            st.metric('99Pay',saldo_s['99Pay'])
        with col4:
            st.metric('C6Invest',saldo_s['C6Invest'])

            
        analytics.aplicacoes_resgates(df,contas_invest)
    


    with tab5:
        df = analytics.anomes(df)
        analytics.extrato(df,anome)


if __name__ == "__main__":
    main()

#input('Pressione ENTER para sair')

