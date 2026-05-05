"""
Эвристическая оценка позиции на основании PST.

Использует бинарное переключение на основании суммы материала. Если сумма
материала в сантипешках меньше 1300, то полагаем, что играется эндшпиль. Иначе
&mdash; миттельшпиль.

Далее на основании этого выберем константы PST для каждого вида фигуры. В данной
оценке все фигуры имеют одинаковые веса, а веса короля зависят от стадии игры.

Веса получены опытным путём. Чем больше вес &mdash; тем выгоднее поставить
фигуру на соответствующее поле.
"""

import chess
from evaluation._pst_const import *

def _get_pst_value(piece_type: chess.PieceType, square: int, is_white: bool) -> int:
    table = PST[piece_type]
    if is_white:
        return table[square]
    else:
        return table[square ^ 56]


def _is_endgame(board: chess.Board) -> bool:
    total_material = 0
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        total_material += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        total_material += len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]
    return total_material <= 1300


def evaluate(board: chess.Board) -> int:
    score = 0
    endgame = _is_endgame(board)

    for piece_type in PIECE_VALUES:
        score += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]

        for square in board.pieces(piece_type, chess.WHITE):
            if piece_type == chess.KING and endgame:
                score += KING_ENDGAME_PST[square]
            else:
                score += _get_pst_value(piece_type, square, is_white=True)

        for square in board.pieces(piece_type, chess.BLACK):
            if piece_type == chess.KING and endgame:
                score -= KING_ENDGAME_PST[square ^ 56]
            else:
                score -= _get_pst_value(piece_type, square, is_white=False)

    return score