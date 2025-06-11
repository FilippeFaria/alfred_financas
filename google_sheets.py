import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Função para autenticar e abrir planilha
@st.cache_resource
def authorize_google_sheets(path):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_file(
        f'{path}/credentials.json',
        scopes=scopes
    )
    
    client = gspread.authorize(creds)
    return client

def get_sheet(path):
    client = authorize_google_sheets(path)  # sua função para autenticar
    spreadsheet = client.open("fluxo_de_caixa")  # abre a planilha pelo nome
    sheet = spreadsheet.sheet1  # pega a primeira aba (Worksheet)
    return sheet

def read_sheet(path):
    sheet = get_sheet(path)  # pega o objeto worksheet
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def limpar_valores_invalidos(x):
    if isinstance(x, (list, dict)):
        return ''  # ou converta para string, se fizer sentido
    return x

# Escrever dados na planilha
def write_sheet(sheet, df):
    df = df.fillna('')  # ou outro valor que preferir
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
