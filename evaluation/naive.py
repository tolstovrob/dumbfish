"""
Наивная материальная оценка.
"""

import chess


VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def evaluate(board: chess.Board) -> int:
    """
    Оценка с точки зрения белых.
    """
    score = 0
    for piece_type, value in VALUES.items():
        score += value * board.pieces_count(piece_type, chess.WHITE)
        score -= value * board.pieces_count(piece_type, chess.BLACK)
    return score