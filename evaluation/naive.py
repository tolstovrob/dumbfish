"""
Материальная наивная оценка позиции
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
    score = 0
    for piece in PIECE_VALUES:
        score += len(board.pieces(piece, chess.WHITE)) * PIECE_VALUES[piece]
        score -= len(board.pieces(piece, chess.BLACK)) * PIECE_VALUES[piece]

    return score