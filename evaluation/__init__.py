import chess
from evaluation.naive import evaluate as naive_evaluate
from evaluation.pst import evaluate as pst_evaluate

EVAL_TYPE = "pst"

def evaluate(board: chess.Board) -> int:
    """Оценка с точки зрения белых. Общие терминальные проверки."""
    
    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    
    match EVAL_TYPE:
        case "naive":
            return naive_evaluate(board)
        case "pst":
            return pst_evaluate(board)