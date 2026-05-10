"""
Modelo de dominio para transacoes pendentes sugeridas por IA.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


PendingTransactionStatus = Literal["pending", "confirmed", "ignored", "auto_confirmed"]


@dataclass
class PendingTransaction:
    id: str
    user_id: str
    source: str
    raw_text: str
    transcription: Optional[str]
    suggested_payload: dict
    confidence: float
    status: PendingTransactionStatus
    created_at: datetime
    updated_at: datetime
