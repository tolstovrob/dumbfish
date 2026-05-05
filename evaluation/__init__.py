from enum import Enum
import chess

from evaluation.naive import evaluate as naive_evaluate
from evaluation.hce_pst import evaluate as hce_pst_evaluate


class EvalType(Enum):
    NAIVE = "naive"
    HCE_PST = "hce_pst"


EVAL_TYPE = EvalType.HCE_PST

_EVALUATORS = {
    EvalType.NAIVE: naive_evaluate,
    EvalType.HCE_PST: hce_pst_evaluate,
}


def evaluate(board: chess.Board) -> int:
    """Оценка с точки зрения белых. Общие терминальные проверки."""
    
    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    
    evaluator = _EVALUATORS.get(EVAL_TYPE)
    if evaluator is None:
        raise ValueError(f"Unknown evaluation type: {EVAL_TYPE}")
    
    return evaluator(board)