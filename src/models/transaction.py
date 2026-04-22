"""
Modelos de dados para transações financeiras.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Transacao:
    """Modelo para uma transação financeira."""
    id: int
    nome: str
    tipo: str  # Receita, Despesa, Transferência, Investimento
    valor: float
    categoria: str
    conta: str
    data: datetime
    obs: str = ""
    tag: Optional[str] = None
    desconsiderar: bool = False
    data_criacao: Optional[str] = None
    parcela: Optional[int] = None
    data_origem: Optional[str] = None

    def to_dict(self) -> dict:
        """Converte a transação para dicionário."""
        return {
            'id': self.id,
            'Nome': self.nome,
            'Tipo': self.tipo,
            'Valor': self.valor,
            'Categoria': self.categoria,
            'Conta': self.conta,
            'Data': self.data.strftime("%Y-%m-%d %H:%M:%S"),
            'Obs': self.obs,
            'TAG': self.tag,
            'desconsiderar': self.desconsiderar,
            'Data Criacao': self.data_criacao,
            'Parcela': self.parcela,
            'Data origem': self.data_origem,
        }


@dataclass
class ValorDesejado:
    """Modelo para valores desejados por categoria."""
    categoria: str
    valor: float
    data: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'Data': self.data.strftime('%d/%m/%Y') if self.data else '',
            'Categoria': self.categoria,
            'Valor': self.valor,
        }