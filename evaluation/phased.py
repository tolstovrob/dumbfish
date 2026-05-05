"""
Продвинутая HCE-оценка с фазовой интерполяцией.

Оценка состоит из эвристик с разными весами в разных стадиях игры:
  - Материал (PIECE_VALUES)
  - PST с фазовой интерполяцией для короля
  - Мобильность (MG/EG таблицы для N/B/R/Q)
  - Пешечные структуры (изолированные, сдвоенные, проходные)
  - Безопасность короля (прикрытие, открытые линии)
  - Пара слонов
  - Ладьи на открытых/полуоткрытых линиях и 7-й горизонтали
  - Кони на форпосте

Фазовая интерполяция: фаза игры вычисляется по интерполянте, что позволяет
добиться более плавного перехода между весами
"""

import chess
from evaluation.shared import VALUES, PST, KING_MG_TABLE, KING_EG_TABLE, flip


PHASE_WEIGHTS = {
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
}
TOTAL_PHASE = 4 * (1 + 1 + 2 + 4)


MOBILITY_MG = {
    chess.KNIGHT: [(-5, 0), (0, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6),
                   (30, 7), (35, 8)],
    chess.BISHOP: [(-10, 0), (0, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6),
                   (30, 7), (35, 8), (40, 9), (45, 10), (50, 11), (55, 12),
                   (60, 13)],
    chess.ROOK:   [(0, 0), (0, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6),
                   (30, 7), (35, 8), (40, 9), (45, 10), (50, 11), (55, 12),
                   (60, 13), (65, 14)],
    chess.QUEEN:  [(0, 0), (0, 1), (2, 2), (4, 3), (6, 4), (8, 5), (10, 6),
                   (12, 7), (14, 8), (16, 9), (18, 10), (20, 11), (22, 12),
                   (24, 13), (26, 14), (28, 15), (30, 16), (32, 17), (34, 18),
                   (36, 19), (38, 20), (40, 21), (42, 22), (44, 23), (46, 24),
                   (48, 25), (50, 26), (52, 27)],
}

MOBILITY_EG = {
    chess.KNIGHT: [(-10, 0), (0, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6),
                   (30, 7), (35, 8)],
    chess.BISHOP: [(-10, 0), (0, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6),
                   (30, 7), (35, 8), (40, 9), (45, 10), (50, 11), (55, 12),
                   (60, 13)],
    chess.ROOK:   [(0, 0), (0, 1), (5, 2), (10, 3), (15, 4), (20, 5), (25, 6),
                   (30, 7), (35, 8), (40, 9), (45, 10), (50, 11), (55, 12),
                   (60, 13), (65, 14)],
    chess.QUEEN:  [(0, 0), (0, 1), (2, 2), (4, 3), (6, 4), (8, 5), (10, 6),
                   (12, 7), (14, 8), (16, 9), (18, 10), (20, 11), (22, 12),
                   (24, 13), (26, 14), (28, 15), (30, 16), (32, 17), (34, 18),
                   (36, 19), (38, 20), (40, 21), (42, 22), (44, 23), (46, 24),
                   (48, 25), (50, 26), (52, 27)],
}

KING_SHIELD = [0, 10, 20, 30, 40, 50, 60, 70, 80]


def _calculate_phase(board: chess.Board) -> float:
    phase = 0
    for pt, w in PHASE_WEIGHTS.items():
        phase += w * len(board.pieces(pt, chess.WHITE))
        phase += w * len(board.pieces(pt, chess.BLACK))
    return phase / TOTAL_PHASE


def _interpolate(mg: int, eg: int, phase: float) -> int:
    return int(mg * phase + eg * (1.0 - phase))


def _mobility(board: chess.Board, phase: float) -> int:
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            for sq in board.pieces(pt, color):
                count = board.attacks_mask(sq) & ~board.occupied_co[color]
                count = count.bit_count()
                mg = next((b for c, b in reversed(MOBILITY_MG[pt]) if count >= c), 0)
                eg = next((b for c, b in reversed(MOBILITY_EG[pt]) if count >= c), 0)
                score += mul * _interpolate(mg, eg, phase)
    return score


def _pawns(board: chess.Board, phase: float) -> int:
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        own = board.pieces(chess.PAWN, color)
        enemy = board.pieces(chess.PAWN, not color)

        for sq in own:
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)

            if not (chess.BB_FILES[file - 1] & own if file > 0 else False) and \
               not (chess.BB_FILES[file + 1] & own if file < 7 else False):
                score += mul * _interpolate(-15, -25, phase)

            if (int(own) & chess.BB_FILES[file]).bit_count() > 1:
                score += mul * _interpolate(-20, -30, phase)

            if color == chess.WHITE:
                blocked = False
                for r in range(rank + 1, 8):
                    if int(enemy) & chess.BB_SQUARES[chess.square(file, r)]:
                        blocked = True
                        break
                    if file > 0 and int(enemy) & chess.BB_SQUARES[chess.square(file - 1, r)]:
                        blocked = True
                        break
                    if file < 7 and int(enemy) & chess.BB_SQUARES[chess.square(file + 1, r)]:
                        blocked = True
                        break
                if not blocked:
                    bonus = [0, 0, 5, 10, 20, 35, 50, 100][rank]
                    score += mul * _interpolate(bonus, bonus * 2, phase)
            else:
                blocked = False
                for r in range(rank - 1, -1, -1):
                    if int(enemy) & chess.BB_SQUARES[chess.square(file, r)]:
                        blocked = True
                        break
                    if file > 0 and int(enemy) & chess.BB_SQUARES[chess.square(file - 1, r)]:
                        blocked = True
                        break
                    if file < 7 and int(enemy) & chess.BB_SQUARES[chess.square(file + 1, r)]:
                        blocked = True
                        break
                if not blocked:
                    bonus = [0, 0, 5, 10, 20, 35, 50, 100][7 - rank]
                    score += mul * _interpolate(bonus, bonus * 2, phase)

    return score


def _king_safety(board: chess.Board, phase: float) -> int:
    if phase < 0.2:
        return 0

    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        ks = board.king(color)
        file = chess.square_file(ks)
        rank = chess.square_rank(ks)

        shield = 0
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                if color == chess.WHITE:
                    for r in range(rank, min(rank + 3, 8)):
                        if board.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, color):
                            shield += 1
                            break
                else:
                    for r in range(rank, max(rank - 3, -1), -1):
                        if board.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, color):
                            shield += 1
                            break
        score += mul * int(KING_SHIELD[min(shield, 8)] * phase)

        penalty = 0
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                own_pawns = int(board.pieces(chess.PAWN, color)) & chess.BB_FILES[f]
                enemy_pawns = int(board.pieces(chess.PAWN, not color)) & chess.BB_FILES[f]
                if not own_pawns:
                    penalty -= 15
                    if not enemy_pawns:
                        penalty -= 10
        score += mul * int(penalty * phase)

    return score


def _bishop_pair(board: chess.Board, phase: float) -> int:
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        bishops = list(board.pieces(chess.BISHOP, color))
        if len(bishops) >= 2:
            sq1, sq2 = bishops[0], bishops[1]
            if (chess.square_file(sq1) + chess.square_rank(sq1)) % 2 != \
               (chess.square_file(sq2) + chess.square_rank(sq2)) % 2:
                score += mul * _interpolate(50, 70, phase)
    return score


def _rooks(board: chess.Board, phase: float) -> int:
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        for sq in board.pieces(chess.ROOK, color):
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)
            own = int(board.pieces(chess.PAWN, color)) & chess.BB_FILES[file]
            enemy = int(board.pieces(chess.PAWN, not color)) & chess.BB_FILES[file]
            if not own:
                if not enemy:
                    score += mul * _interpolate(25, 35, phase)
                else:
                    score += mul * _interpolate(15, 20, phase)
            if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
                score += mul * _interpolate(20, 30, phase)
    return score


def _knights(board: chess.Board, phase: float) -> int:
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        for sq in board.pieces(chess.KNIGHT, color):
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)
            if (color == chess.WHITE and rank < 4) or (color == chess.BLACK and rank > 3):
                continue
            pawn_rank = rank - 1 if color == chess.WHITE else rank + 1
            if 0 <= pawn_rank <= 7:
                if board.piece_at(chess.square(file, pawn_rank)) == chess.Piece(chess.PAWN, color):
                    attacked = False
                    enemy_pawns = int(board.pieces(chess.PAWN, not color))
                    atk_rank = rank + 1 if color == chess.WHITE else rank - 1
                    for af in [file - 1, file + 1]:
                        if 0 <= af <= 7 and 0 <= atk_rank <= 7:
                            if enemy_pawns & chess.BB_SQUARES[chess.square(af, atk_rank)]:
                                attacked = True
                                break
                    if not attacked:
                        score += mul * _interpolate(15, 10, phase)
    return score


def evaluate(board: chess.Board) -> int:
    phase = _calculate_phase(board)
    score = 0

    for pt, val in VALUES.items():
        score += val * len(board.pieces(pt, chess.WHITE))
        score -= val * len(board.pieces(pt, chess.BLACK))

    for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        for sq in board.pieces(pt, chess.WHITE):
            table = PST[pt]
            score += table[sq]
        for sq in board.pieces(pt, chess.BLACK):
            table = PST[pt]
            score -= table[flip(sq)]

    for sq in board.pieces(chess.KING, chess.WHITE):
        score += _interpolate(KING_MG_TABLE[sq], KING_EG_TABLE[sq], phase)
    for sq in board.pieces(chess.KING, chess.BLACK):
        score -= _interpolate(KING_MG_TABLE[flip(sq)], KING_EG_TABLE[flip(sq)], phase)

    score += _mobility(board, phase)
    score += _pawns(board, phase)
    score += _king_safety(board, phase)
    score += _bishop_pair(board, phase)
    score += _rooks(board, phase)
    score += _knights(board, phase)

    return score