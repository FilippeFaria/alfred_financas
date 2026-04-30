from pathlib import Path

import pandas as pd

from src.services.google_sheets import read_valores_desejados
from src.services.data_handler import _normalizar_datas, carregar_dados


ROOT_PATH = Path(__file__).resolve().parents[2]


def carregar_dados_financeiros() -> pd.DataFrame:
    """Carrega os dados financeiros com fallback para CSV local."""
    try:
        return carregar_dados(str(ROOT_PATH))
    except Exception as exc:
        csv_path = ROOT_PATH / "fluxo_de_caixa.csv"
        if not csv_path.exists():
            raise RuntimeError(
                "Nao foi possivel carregar dados do Google Sheets e nao ha CSV local de fallback."
            ) from exc

        df = pd.read_csv(
            csv_path,
            sep=";",
            encoding="latin1",
            decimal=",",
            parse_dates=["Data"],
            dayfirst=True,
        )
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df["desconsiderar"] = df["desconsiderar"].astype(str).str.upper().replace(
            {"TRUE": True, "FALSE": False}
        )
        if "Categoria" in df.columns:
            df["Categoria"] = df["Categoria"].str.replace(
                "TV.Internet.Telefone", "Assinaturas", regex=False
            )

        return _normalizar_datas(df)


def carregar_valores_desejados() -> dict[str, float]:
    """Carrega o orcamento desejado por categoria com fallback para dicionario vazio."""
    try:
        df_valores = read_valores_desejados(str(ROOT_PATH))
    except Exception:
        return {}

    if df_valores.empty or "Categoria" not in df_valores.columns or "Valor" not in df_valores.columns:
        return {}

    df_valores = df_valores.copy()
    df_valores["Valor"] = pd.to_numeric(df_valores["Valor"], errors="coerce")
    df_valores = df_valores.dropna(subset=["Categoria", "Valor"])
    df_valores = df_valores[df_valores["Valor"] > 0]
    return {
        str(linha["Categoria"]).strip(): float(linha["Valor"])
        for _, linha in df_valores.iterrows()
    }
