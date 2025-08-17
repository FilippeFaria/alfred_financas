import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# Função para autenticar e abrir planilha
@st.cache_resource
def authorize_google_sheets(path):
    if path == '.':
        # Carregar as credenciais dos secrets
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        print('Tamo online')
    
    else:
        print('Tamo offline')
        # Se falhar, carrega do arquivo local (uso local)
        with open(f'{path}/credentials.json') as f:
            creds_dict = json.load(f)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def get_sheet(path):
    client = authorize_google_sheets(path)  # sua função para autenticar
    spreadsheet = client.open("fluxo_de_caixa")  # abre a planilha pelo nome
    sheet = spreadsheet.sheet1  # pega a primeira aba (Worksheet)
    return sheet

@st.cache_data
def read_sheet(path,trigger=None):
    sheet = get_sheet(path)  # pega o objeto worksheet
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Corrigir todas as colunas que contêm valores numéricos com vírgula decimal
    for col in df.columns:
        # Substitui vírgula por ponto e tenta converter para float
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='ignore')
    return df




def limpar_valores_invalidos(x):
    if isinstance(x, (list, dict)):
        return ''  # ou converta para string, se fizer sentido
    return x

# Escrever dados na planilha
def write_sheet(sheet, df):
    df = df.fillna('')  # ou outro valor que preferir]
    df['Valor'] = df['Valor'].astype(str)
    df = df.applymap(limpar_valores_invalidos)
    sheet.update([df.columns.values.tolist()] + df.values.tolist())



# # --- Streamlit app ---

# sheet = get_sheet()

# st.title("Meu App com Google Sheets")

# df = read_sheet(sheet)

# st.dataframe(df)

# # Exemplo: editar dataframe (simplificado)
# if st.button("Adicionar linha"):
#     nova_linha = {"Coluna1": "Valor novo", "Coluna2": 123}  # Ajuste para suas colunas
#     df = df.append(nova_linha, ignore_index=True)
#     write_sheet(sheet, df)
#     st.success("Linha adicionada!")

# st.dataframe(df)
