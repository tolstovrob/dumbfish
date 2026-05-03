import chess
from evaluation.naive import evaluate as naive_evaluate
from evaluation.heuristic import evaluate as heuristic_evaluate

EVAL_TYPE = "heuristic"

def evaluate(board: chess.Board) -> int:
    """Оценка с точки зрения белых. Общие терминальные проверки."""
    
    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    
    match EVAL_TYPE:
        case "naive":
            return naive_evaluate(board)
        case "heuristic":
            return heuristic_evaluate(board)