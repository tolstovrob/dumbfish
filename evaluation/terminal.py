import chess

def score(board: chess.Board) -> int | None:
    """None &mdash; не терминал, иначе оценка"""
    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    return None