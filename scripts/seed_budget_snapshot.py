"""Seed inicial da tabela budgets no PostgreSQL/Supabase."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from src.database.connection import SessionLocal
from src.database.repositories import BudgetRepository, UserRepository


DATA_BASE = datetime.strptime("05/05/2026", "%d/%m/%Y")
VALORES_BASE = {
    "Assinaturas": 708.0,
    "Casa": 3841.81,
    "Compras": 1200.0,
    "Cosméticos": 200.0,
    "Educação": 39.9,
    "Lazer": 700.0,
    "Multas": 0.0,
    "Onix": 0.0,
    "Outros": 0.0,
    "Presentes": 800.0,
    "Restaurante": 1700.0,
    "Saúde": 400.0,
    "Serviços": 700.91,
    "Supermercado": 2200.0,
    "Transporte": 1000.0,
    "Viagem": 500.0,
}


def main() -> None:
    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        BudgetRepository(db).create_snapshot(
            user_id=user.id,
            data=DATA_BASE,
            valores=VALORES_BASE,
        )
        db.commit()
        print(f"Snapshot de orçamento salvo para {len(VALORES_BASE)} categorias em {DATA_BASE:%d/%m/%Y}.")


if __name__ == "__main__":
    main()
