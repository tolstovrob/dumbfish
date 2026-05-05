"""
HCE-оценка на основе PST таблиц с бинарным определением окончания.

Оценка складывается из материального веса фигур, а также позиционных таблиц для
всех фигур &mdash; бонус/штраф за расположение.

Вес короля в PST высчитывается особенным образом &mdash; в разных этапах игры
(миттельшпиль и окончание).

Критерий окончания бинарен &mdash; 2600 сантипешек
"""


import chess
from evaluation.shared import *


def _pst(piece_type: chess.PieceType, sq: int, side: chess.Color) -> int:
    table = PST[piece_type]
    return table[sq] if side == chess.WHITE else table[flip(sq)]


def _is_endgame(board: chess.Board) -> bool:
    material = 0
    for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        material += VALUES[pt] * len(board.pieces(pt, chess.WHITE))
        material += VALUES[pt] * len(board.pieces(pt, chess.BLACK))
    return material <= 2600


def evaluate(board: chess.Board) -> int:
    score = 0
    endgame = _is_endgame(board)

    for pt, val in VALUES.items():
        score += val * len(board.pieces(pt, chess.WHITE))
        score -= val * len(board.pieces(pt, chess.BLACK))

    for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        for sq in board.pieces(pt, chess.WHITE):
            score += _pst(pt, sq, chess.WHITE)
        for sq in board.pieces(pt, chess.BLACK):
            score -= _pst(pt, sq, chess.BLACK)

    for sq in board.pieces(chess.KING, chess.WHITE):
        table = KING_EG_TABLE if endgame else KING_MG_TABLE
        score += table[sq]

    for sq in board.pieces(chess.KING, chess.BLACK):
        table = KING_EG_TABLE if endgame else KING_MG_TABLE
        score -= table[flip(sq)]

    return score