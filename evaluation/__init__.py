from typing import Callable
from enum import Enum
import chess
from evaluation.terminal import score as terminal_score
from evaluation.naive import evaluate as naive_evaluate
from evaluation.pst import evaluate as pst_evaluate
from evaluation.phased import evaluate as phased_evaluate
from evaluation.nnue import get_nnue

class EvalType(Enum):
    NAIVE = "naive"
    PST = "pst"
    PHASED = "phased"
    NNUE = "nnue"


EVAL_TYPE = EvalType.NNUE

_EVALUATORS: dict[EvalType, Callable[[chess.Board], int]] = {
    EvalType.NAIVE: naive_evaluate,
    EvalType.PST: pst_evaluate,
    EvalType.PHASED: phased_evaluate,
    EvalType.NNUE: lambda board: get_nnue("../dumbfish/test_weights.npz").evaluate(board)
}


def evaluate(board: chess.Board) -> int:
    term = terminal_score(board)
    if term is not None:
        return term
    
    return _EVALUATORS[EVAL_TYPE](board)