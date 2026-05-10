from __future__ import annotations

from .schemas import CampoPendente


def calcular_confianca(*, pendencias: list[CampoPendente], avisos: list[str], justificativa: str | None = None) -> float:
    score = 1.0
    score -= min(len(pendencias) * 0.15, 0.75)
    score -= min(len(avisos) * 0.1, 0.5)
    if justificativa and ("talvez" in justificativa.lower() or "incerto" in justificativa.lower()):
        score -= 0.1
    return max(0.0, min(score, 1.0))
