"""
Фазовая HCE оценка позиции.
"""

import chess
from evaluation.terminal import score as terminal_score
from evaluation.phased import evaluate as phased_evaluate


def evaluate(board: chess.Board) -> int:
    """Оценка позиции с точки зрения белых."""
    term = terminal_score(board)
    if term is not None:
        return term
    
    return phased_evaluate(board)
