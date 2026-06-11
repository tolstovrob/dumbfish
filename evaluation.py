"""
Фазовая HCE оценка шахматной позиции.

Оценка состоит из эвристик с разными весами в разных стадиях игры:
  - Материал (VALUES)
  - PST с фазовой интерполяцией для короля
  - Мобильность (MG/EG таблицы для N/B/R/Q)
  - Пешечные структуры (изолированные, сдвоенные, проходные)
  - Безопасность короля (прикрытие, открытые линии)
  - Пара слонов
  - Ладьи на открытых/полуоткрытых линиях и 7-й горизонтали
  - Кони на форпосте

Фаза игры вычисляется по интерполянте, что позволяет добиться более плавного
перехода между весами миттельшпиля и эндшпиля.
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

PAWN_TABLE = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    10,
    10,
    20,
    30,
    30,
    20,
    10,
    10,
    5,
    5,
    10,
    25,
    25,
    10,
    5,
    5,
    0,
    0,
    0,
    20,
    20,
    0,
    0,
    0,
    5,
    -5,
    -10,
    0,
    0,
    -10,
    -5,
    5,
    5,
    10,
    10,
    -20,
    -20,
    10,
    10,
    5,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]

KNIGHT_TABLE = [
    -50,
    -40,
    -30,
    -30,
    -30,
    -30,
    -40,
    -50,
    -40,
    -20,
    0,
    0,
    0,
    0,
    -20,
    -40,
    -30,
    0,
    10,
    15,
    15,
    10,
    0,
    -30,
    -30,
    5,
    15,
    20,
    20,
    15,
    5,
    -30,
    -30,
    0,
    15,
    20,
    20,
    15,
    0,
    -30,
    -30,
    5,
    10,
    15,
    15,
    10,
    5,
    -30,
    -40,
    -20,
    0,
    5,
    5,
    0,
    -20,
    -40,
    -50,
    -40,
    -30,
    -30,
    -30,
    -30,
    -40,
    -50,
]

BISHOP_TABLE = [
    -20,
    -10,
    -10,
    -10,
    -10,
    -10,
    -10,
    -20,
    -10,
    0,
    0,
    0,
    0,
    0,
    0,
    -10,
    -10,
    0,
    10,
    10,
    10,
    10,
    0,
    -10,
    -10,
    5,
    5,
    10,
    10,
    5,
    5,
    -10,
    -10,
    0,
    5,
    10,
    10,
    5,
    0,
    -10,
    -10,
    10,
    10,
    10,
    10,
    10,
    10,
    -10,
    -10,
    5,
    0,
    0,
    0,
    0,
    5,
    -10,
    -20,
    -10,
    -10,
    -10,
    -10,
    -10,
    -10,
    -20,
]

ROOK_TABLE = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    5,
    10,
    10,
    10,
    10,
    10,
    10,
    5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    0,
    0,
    0,
    5,
    5,
    0,
    0,
    0,
]

QUEEN_TABLE = [
    -20,
    -10,
    -10,
    -5,
    -5,
    -10,
    -10,
    -20,
    -10,
    0,
    0,
    0,
    0,
    0,
    0,
    -10,
    -10,
    0,
    5,
    5,
    5,
    5,
    0,
    -10,
    -5,
    0,
    5,
    5,
    5,
    5,
    0,
    -5,
    0,
    0,
    5,
    5,
    5,
    5,
    0,
    -5,
    -10,
    5,
    5,
    5,
    5,
    5,
    0,
    -10,
    -10,
    0,
    5,
    0,
    0,
    0,
    0,
    -10,
    -20,
    -10,
    -10,
    -5,
    -5,
    -10,
    -10,
    -20,
]

KING_MG_TABLE = [
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -20,
    -30,
    -30,
    -40,
    -40,
    -30,
    -30,
    -20,
    -10,
    -20,
    -20,
    -20,
    -20,
    -20,
    -20,
    -10,
    20,
    20,
    0,
    0,
    0,
    0,
    20,
    20,
    20,
    30,
    10,
    0,
    0,
    10,
    30,
    20,
]

KING_EG_TABLE = [
    -50,
    -40,
    -30,
    -20,
    -20,
    -30,
    -40,
    -50,
    -30,
    -20,
    -10,
    0,
    0,
    -10,
    -20,
    -30,
    -30,
    -10,
    20,
    30,
    30,
    20,
    -10,
    -30,
    -30,
    -10,
    30,
    40,
    40,
    30,
    -10,
    -30,
    -30,
    -10,
    30,
    40,
    40,
    30,
    -10,
    -30,
    -30,
    -10,
    20,
    30,
    30,
    20,
    -10,
    -30,
    -30,
    -30,
    0,
    0,
    0,
    0,
    -30,
    -30,
    -50,
    -30,
    -30,
    -30,
    -30,
    -30,
    -30,
    -50,
]

PST = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}

PHASE_WEIGHTS = {
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
}
TOTAL_PHASE = 4 * (1 + 1 + 2 + 4)

MOBILITY_MG = {
    chess.KNIGHT: [
        (-5, 0),
        (0, 1),
        (5, 2),
        (10, 3),
        (15, 4),
        (20, 5),
        (25, 6),
        (30, 7),
        (35, 8),
    ],
    chess.BISHOP: [
        (-10, 0),
        (0, 1),
        (5, 2),
        (10, 3),
        (15, 4),
        (20, 5),
        (25, 6),
        (30, 7),
        (35, 8),
        (40, 9),
        (45, 10),
        (50, 11),
        (55, 12),
        (60, 13),
    ],
    chess.ROOK: [
        (0, 0),
        (0, 1),
        (5, 2),
        (10, 3),
        (15, 4),
        (20, 5),
        (25, 6),
        (30, 7),
        (35, 8),
        (40, 9),
        (45, 10),
        (50, 11),
        (55, 12),
        (60, 13),
        (65, 14),
    ],
    chess.QUEEN: [
        (0, 0),
        (0, 1),
        (2, 2),
        (4, 3),
        (6, 4),
        (8, 5),
        (10, 6),
        (12, 7),
        (14, 8),
        (16, 9),
        (18, 10),
        (20, 11),
        (22, 12),
        (24, 13),
        (26, 14),
        (28, 15),
        (30, 16),
        (32, 17),
        (34, 18),
        (36, 19),
        (38, 20),
        (40, 21),
        (42, 22),
        (44, 23),
        (46, 24),
        (48, 25),
        (50, 26),
        (52, 27),
    ],
}

MOBILITY_EG = {
    chess.KNIGHT: [
        (-10, 0),
        (0, 1),
        (5, 2),
        (10, 3),
        (15, 4),
        (20, 5),
        (25, 6),
        (30, 7),
        (35, 8),
    ],
    chess.BISHOP: [
        (-10, 0),
        (0, 1),
        (5, 2),
        (10, 3),
        (15, 4),
        (20, 5),
        (25, 6),
        (30, 7),
        (35, 8),
        (40, 9),
        (45, 10),
        (50, 11),
        (55, 12),
        (60, 13),
    ],
    chess.ROOK: [
        (0, 0),
        (0, 1),
        (5, 2),
        (10, 3),
        (15, 4),
        (20, 5),
        (25, 6),
        (30, 7),
        (35, 8),
        (40, 9),
        (45, 10),
        (50, 11),
        (55, 12),
        (60, 13),
        (65, 14),
    ],
    chess.QUEEN: [
        (0, 0),
        (0, 1),
        (2, 2),
        (4, 3),
        (6, 4),
        (8, 5),
        (10, 6),
        (12, 7),
        (14, 8),
        (16, 9),
        (18, 10),
        (20, 11),
        (22, 12),
        (24, 13),
        (26, 14),
        (28, 15),
        (30, 16),
        (32, 17),
        (34, 18),
        (36, 19),
        (38, 20),
        (40, 21),
        (42, 22),
        (44, 23),
        (46, 24),
        (48, 25),
        (50, 26),
        (52, 27),
    ],
}

ISOLATED_MG = -15
ISOLATED_EG = -25
DOUBLED_MG = -20
DOUBLED_EG = -30
PASSED = [0, 0, 5, 10, 20, 35, 50, 100]
PASSED_EG_MULT = 2.0

SHIELD = [0, 10, 20, 30, 40, 50, 60, 70, 80]
OPEN_FILE = -15
HALF_OPEN_FILE = -10
SAFETY_PHASE_MIN = 0.2

BISHOP_PAIR_MG = 50
BISHOP_PAIR_EG = 70

ROOK_OPEN_MG = 25
ROOK_OPEN_EG = 35
ROOK_SEMIOPEN_MG = 15
ROOK_SEMIOPEN_EG = 20
ROOK_7TH_MG = 20
ROOK_7TH_EG = 30

OUTPOST_MG = 15
OUTPOST_EG = 10


def _terminal_score(board: chess.Board) -> int | None:
    """None — не терминал, иначе оценка мата/пата."""
    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    return None


def _flip(sq: int) -> int:
    """Зеркалирование клетки для чёрных (вертикальная симметрия)."""
    return sq ^ 56


def _calculate_phase(board: chess.Board) -> float:
    """Вычисление фазы игры (0.0 = эндшпиль, 1.0 = миттельшпиль)."""
    phase = 0
    for pt, w in PHASE_WEIGHTS.items():
        phase += w * len(board.pieces(pt, chess.WHITE))
        phase += w * len(board.pieces(pt, chess.BLACK))
    return min(1.0, max(0.0, phase / TOTAL_PHASE))


def _interpolate(mg: int, eg: int, phase: float) -> int:
    """Интерполяция между миттельшпилем (mg) и эндшпилем (eg)."""
    return int(mg * phase + eg * (1.0 - phase))


def _pst_score(board: chess.Board, phase: float) -> int:
    """Оценка Piece-Square Tables для всех фигур, кроме короля."""
    score = 0
    for pt, table in PST.items():
        for sq in board.pieces(pt, chess.WHITE):
            score += table[sq]
        for sq in board.pieces(pt, chess.BLACK):
            score -= table[_flip(sq)]
    return score


def _king_score(board: chess.Board, phase: float) -> int:
    """Оценка короля с интерполяцией между MG и EG таблицами."""
    score = 0
    for sq in board.pieces(chess.KING, chess.WHITE):
        score += _interpolate(KING_MG_TABLE[sq], KING_EG_TABLE[sq], phase)
    for sq in board.pieces(chess.KING, chess.BLACK):
        score -= _interpolate(KING_MG_TABLE[_flip(sq)], KING_EG_TABLE[_flip(sq)], phase)
    return score


def _mobility_score(board: chess.Board, phase: float) -> int:
    """Оценка мобильности фигур."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            for sq in board.pieces(pt, color):
                count = (board.attacks_mask(sq) & ~board.occupied_co[color]).bit_count()
                mg = next((b for c, b in reversed(MOBILITY_MG[pt]) if count >= c), 0)
                eg = next((b for c, b in reversed(MOBILITY_EG[pt]) if count >= c), 0)
                score += mul * _interpolate(mg, eg, phase)
    return score


def _pawns_score(board: chess.Board, phase: float) -> int:
    """Оценка пешечной структуры."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        own = board.pieces(chess.PAWN, color)
        enemy = board.pieces(chess.PAWN, not color)
        own_mask = int(own)
        enemy_mask = int(enemy)

        for sq in own:
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)

            left_file = file - 1
            right_file = file + 1
            left_ok = left_file >= 0 and (chess.BB_FILES[left_file] & own_mask)
            right_ok = right_file <= 7 and (chess.BB_FILES[right_file] & own_mask)
            if not left_ok and not right_ok:
                score += mul * _interpolate(ISOLATED_MG, ISOLATED_EG, phase)

            if (own_mask & chess.BB_FILES[file]).bit_count() > 1:
                score += mul * _interpolate(DOUBLED_MG, DOUBLED_EG, phase)

            if color == chess.WHITE:
                blocked = False
                for r in range(rank + 1, 8):
                    sq_check = chess.square(file, r)
                    if enemy_mask & chess.BB_SQUARES[sq_check]:
                        blocked = True
                        break
                    if (
                        file > 0
                        and enemy_mask & chess.BB_SQUARES[chess.square(file - 1, r)]
                    ):
                        blocked = True
                        break
                    if (
                        file < 7
                        and enemy_mask & chess.BB_SQUARES[chess.square(file + 1, r)]
                    ):
                        blocked = True
                        break
                if not blocked:
                    bonus = PASSED[rank]
                    score += mul * _interpolate(
                        bonus, int(bonus * PASSED_EG_MULT), phase
                    )
            else:
                blocked = False
                for r in range(rank - 1, -1, -1):
                    sq_check = chess.square(file, r)
                    if enemy_mask & chess.BB_SQUARES[sq_check]:
                        blocked = True
                        break
                    if (
                        file > 0
                        and enemy_mask & chess.BB_SQUARES[chess.square(file - 1, r)]
                    ):
                        blocked = True
                        break
                    if (
                        file < 7
                        and enemy_mask & chess.BB_SQUARES[chess.square(file + 1, r)]
                    ):
                        blocked = True
                        break
                if not blocked:
                    bonus = PASSED[7 - rank]
                    score += mul * _interpolate(
                        bonus, int(bonus * PASSED_EG_MULT), phase
                    )

    return score


def _king_safety_score(board: chess.Board, phase: float) -> int:
    """Оценка безопасности короля."""
    if phase < SAFETY_PHASE_MIN:
        return 0

    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        ks = board.king(color)
        if ks is None:
            continue
        file = chess.square_file(ks)
        rank = chess.square_rank(ks)

        shield = 0
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                if color == chess.WHITE:
                    for r in range(rank, min(rank + 3, 8)):
                        if board.piece_at(chess.square(f, r)) == chess.Piece(
                            chess.PAWN, color
                        ):
                            shield += 1
                            break
                else:
                    for r in range(rank, max(rank - 3, -1), -1):
                        if board.piece_at(chess.square(f, r)) == chess.Piece(
                            chess.PAWN, color
                        ):
                            shield += 1
                            break
        score += mul * int(SHIELD[min(shield, 8)] * phase)

        penalty = 0
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                own_pawns = int(board.pieces(chess.PAWN, color)) & chess.BB_FILES[f]
                enemy_pawns = (
                    int(board.pieces(chess.PAWN, not color)) & chess.BB_FILES[f]
                )
                if not own_pawns:
                    penalty += OPEN_FILE
                    if not enemy_pawns:
                        penalty += HALF_OPEN_FILE
        score += mul * int(penalty * phase)

    return score


def _bishop_pair_score(board: chess.Board, phase: float) -> int:
    """Оценка за пару слонов на разноцветных полях."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        bishops = list(board.pieces(chess.BISHOP, color))
        if len(bishops) >= 2:
            sq1, sq2 = bishops[0], bishops[1]
            if (chess.square_file(sq1) + chess.square_rank(sq1)) % 2 != (
                chess.square_file(sq2) + chess.square_rank(sq2)
            ) % 2:
                score += mul * _interpolate(BISHOP_PAIR_MG, BISHOP_PAIR_EG, phase)
    return score


def _rooks_score(board: chess.Board, phase: float) -> int:
    """Оценка ладей (открытые линии, 7-я горизонталь)."""
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
                    score += mul * _interpolate(ROOK_OPEN_MG, ROOK_OPEN_EG, phase)
                else:
                    score += mul * _interpolate(
                        ROOK_SEMIOPEN_MG, ROOK_SEMIOPEN_EG, phase
                    )
            if (color == chess.WHITE and rank == 6) or (
                color == chess.BLACK and rank == 1
            ):
                score += mul * _interpolate(ROOK_7TH_MG, ROOK_7TH_EG, phase)
    return score


def _knights_score(board: chess.Board, phase: float) -> int:
    """Оценка коней на форпосте."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        for sq in board.pieces(chess.KNIGHT, color):
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)
            if (color == chess.WHITE and rank < 4) or (
                color == chess.BLACK and rank > 3
            ):
                continue
            pawn_rank = rank - 1 if color == chess.WHITE else rank + 1
            if 0 <= pawn_rank <= 7:
                if board.piece_at(chess.square(file, pawn_rank)) == chess.Piece(
                    chess.PAWN, color
                ):
                    attacked = False
                    enemy_pawns = int(board.pieces(chess.PAWN, not color))
                    atk_rank = rank + 1 if color == chess.WHITE else rank - 1
                    for af in [file - 1, file + 1]:
                        if 0 <= af <= 7 and 0 <= atk_rank <= 7:
                            if (
                                enemy_pawns
                                & chess.BB_SQUARES[chess.square(af, atk_rank)]
                            ):
                                attacked = True
                                break
                    if not attacked:
                        score += mul * _interpolate(OUTPOST_MG, OUTPOST_EG, phase)
    return score


def evaluate(board: chess.Board) -> int:
    """
    Полная фазовая HCE оценка позиции с точки зрения белых.
    Учитывает терминальные позиции (мат, пат).
    """
    term = _terminal_score(board)
    if term is not None:
        return term

    phase = _calculate_phase(board)
    score = 0

    for pt, val in VALUES.items():
        score += val * len(board.pieces(pt, chess.WHITE))
        score -= val * len(board.pieces(pt, chess.BLACK))

    score += _pst_score(board, phase)

    score += _king_score(board, phase)

    score += _mobility_score(board, phase)
    score += _pawns_score(board, phase)
    score += _king_safety_score(board, phase)
    score += _bishop_pair_score(board, phase)
    score += _rooks_score(board, phase)
    score += _knights_score(board, phase)

    return score
