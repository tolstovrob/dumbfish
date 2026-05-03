"""
Модуль оценки позиции
"""

import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def evaluate(board: chess.Board) -> int:
    """Оценка позиции в сантипешках с точки зрения белых"""

    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000

    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    
    score = 0
    for piece in PIECE_VALUES:
        score += len(board.pieces(piece, chess.WHITE)) * PIECE_VALUES[piece]
        score -= len(board.pieces(piece, chess.BLACK)) * PIECE_VALUES[piece]

    return score