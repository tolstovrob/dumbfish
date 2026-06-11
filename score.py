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
from pst import *


def _flip(sq: int) -> int:
    """Зеркалирование для чёрных."""
    return sq ^ 56


def calculate_phase(board: chess.Board) -> tuple[float, float, float]:
    """
    Вычисление трёх фаз игры.
    Возвращает (weight_opening, weight_middlegame, weight_endgame)
    """
    phase = 0
    for pt, w in PHASE_WEIGHTS.items():
        if pt == chess.PAWN or pt == chess.KING:
            continue
        phase += w * len(board.pieces(pt, chess.WHITE))
        phase += w * len(board.pieces(pt, chess.BLACK))

    t = min(1.0, max(0.0, phase / MAX_PHASE))

    if t < 0.3:
        w_open = 1.0 - t / 0.3
        w_mid = t / 0.3
        w_end = 0.0
    elif t < 0.7:
        w_open = 0.0
        w_mid = 1.0
        w_end = 0.0
    else:
        w_open = 0.0
        w_mid = 1.0 - (t - 0.7) / 0.3
        w_end = (t - 0.7) / 0.3

    return w_open, w_mid, w_end


def _interpolate(
    opening: int,
    middlegame: int,
    endgame: int,
    weights: tuple[float, float, float],
) -> int:
    """Трёхфазная интерполяция."""
    w_open, w_mid, w_end = weights
    return int(opening * w_open + middlegame * w_mid + endgame * w_end)


def _terminal_score(board: chess.Board) -> int | None:
    """Проверка терминальных позиций."""
    if board.is_checkmate():
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    return None


def _pst_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка PST с трёхфазной интерполяцией."""
    score = 0
    for pt, (opening, middlegame, endgame) in PST_PHASE.items():
        if pt == chess.KING:
            continue
        for sq in board.pieces(pt, chess.WHITE):
            score += _interpolate(opening[sq], middlegame[sq], endgame[sq], weights)
        for sq in board.pieces(pt, chess.BLACK):
            score -= _interpolate(
                opening[_flip(sq)],
                middlegame[_flip(sq)],
                endgame[_flip(sq)],
                weights,
            )
    return score


def _king_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка короля."""
    score = 0
    opening, middlegame, endgame = PST_PHASE[chess.KING]
    for sq in board.pieces(chess.KING, chess.WHITE):
        score += _interpolate(opening[sq], middlegame[sq], endgame[sq], weights)
    for sq in board.pieces(chess.KING, chess.BLACK):
        score -= _interpolate(
            opening[_flip(sq)],
            middlegame[_flip(sq)],
            endgame[_flip(sq)],
            weights,
        )
    return score


def _mobility_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка мобильности."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            for sq in board.pieces(pt, color):
                count = (board.attacks_mask(sq) & ~board.occupied_co[color]).bit_count()

                open_bonus = next(
                    (b for c, b in reversed(MOBILITY_OPENING[pt]) if count >= c), 0
                )
                mid_bonus = next(
                    (b for c, b in reversed(MOBILITY_MIDDLEGAME[pt]) if count >= c), 0
                )
                end_bonus = next(
                    (b for c, b in reversed(MOBILITY_ENDGAME[pt]) if count >= c), 0
                )

                score += mul * _interpolate(open_bonus, mid_bonus, end_bonus, weights)
    return score


def _pawns_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка пешечной структуры с трёхфазной интерполяцией."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        own = board.pieces(chess.PAWN, color)
        enemy = board.pieces(chess.PAWN, not color)
        own_mask = int(own)

        for sq in own:
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)

            left_ok = file > 0 and (chess.BB_FILES[file - 1] & own_mask)
            right_ok = file < 7 and (chess.BB_FILES[file + 1] & own_mask)
            if not left_ok and not right_ok:
                score += mul * _interpolate(
                    ISOLATED[0], ISOLATED[1], ISOLATED[2], weights
                )

            if (own_mask & chess.BB_FILES[file]).bit_count() > 1:
                score += mul * _interpolate(DOUBLED[0], DOUBLED[1], DOUBLED[2], weights)

            is_passed = True
            if color == chess.WHITE:
                for r in range(rank + 1, 8):
                    sq_check = chess.square(file, r)
                    if chess.BB_SQUARES[sq_check] & int(enemy):
                        is_passed = False
                        break
                    if file > 0 and chess.BB_SQUARES[chess.square(file - 1, r)] & int(
                        enemy
                    ):
                        is_passed = False
                        break
                    if file < 7 and chess.BB_SQUARES[chess.square(file + 1, r)] & int(
                        enemy
                    ):
                        is_passed = False
                        break
            else:
                for r in range(rank - 1, -1, -1):
                    sq_check = chess.square(file, r)
                    if chess.BB_SQUARES[sq_check] & int(enemy):
                        is_passed = False
                        break
                    if file > 0 and chess.BB_SQUARES[chess.square(file - 1, r)] & int(
                        enemy
                    ):
                        is_passed = False
                        break
                    if file < 7 and chess.BB_SQUARES[chess.square(file + 1, r)] & int(
                        enemy
                    ):
                        is_passed = False
                        break

            if is_passed:
                if color == chess.WHITE:
                    bonus = PASSED_BASE[rank]
                else:
                    bonus = PASSED_BASE[7 - rank]

                score += mul * _interpolate(
                    bonus,
                    int(bonus * PASSED_BONUS_MG),
                    int(bonus * PASSED_BONUS_EG),
                    weights,
                )

    return score


def _king_safety_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка безопасности короля."""
    w_open, w_mid, w_end = weights
    if w_mid + w_end < SAFETY_PHASE_MIN:
        return 0

    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        ks = board.king(color)
        if ks is None:
            continue

        file = chess.square_file(ks)
        rank = chess.square_rank(ks)

        shield_count = 0
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                if color == chess.WHITE:
                    for r in range(rank, min(rank + 3, 8)):
                        if board.piece_at(chess.square(f, r)) == chess.Piece(
                            chess.PAWN, color
                        ):
                            shield_count += 1
                            break
                else:
                    for r in range(rank, max(rank - 3, -1), -1):
                        if board.piece_at(chess.square(f, r)) == chess.Piece(
                            chess.PAWN, color
                        ):
                            shield_count += 1
                            break

        shield_val = SHIELD_VALUES[min(shield_count, 8)]
        score += mul * _interpolate(
            int(shield_val * SHIELD_PHASE_WEIGHTS[0]),
            int(shield_val * SHIELD_PHASE_WEIGHTS[1]),
            int(shield_val * SHIELD_PHASE_WEIGHTS[2]),
            weights,
        )

        if w_open > w_mid:
            phase_idx = 0
        elif w_end > w_mid:
            phase_idx = 2
        else:
            phase_idx = 1

        penalty = 0
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                own_pawns = int(board.pieces(chess.PAWN, color)) & chess.BB_FILES[f]
                enemy_pawns = (
                    int(board.pieces(chess.PAWN, not color)) & chess.BB_FILES[f]
                )
                if not own_pawns:
                    penalty += OPEN_FILE_PENALTY[phase_idx]
                    if not enemy_pawns:
                        penalty += HALF_OPEN_PENALTY[phase_idx]

        score += mul * _interpolate(penalty, penalty, penalty, weights)

    return score


def _bishop_pair_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка за пару слонов."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mul = 1 if color == chess.WHITE else -1
        bishops = list(board.pieces(chess.BISHOP, color))
        if len(bishops) >= 2:
            sq1, sq2 = bishops[0], bishops[1]
            if (chess.square_file(sq1) + chess.square_rank(sq1)) % 2 != (
                chess.square_file(sq2) + chess.square_rank(sq2)
            ) % 2:
                score += mul * _interpolate(
                    BISHOP_PAIR[0], BISHOP_PAIR[1], BISHOP_PAIR[2], weights
                )
    return score


def _rooks_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
    """Оценка ладей."""
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
                    score += mul * _interpolate(
                        ROOK_OPEN[0], ROOK_OPEN[1], ROOK_OPEN[2], weights
                    )
                else:
                    score += mul * _interpolate(
                        ROOK_SEMIOPEN[0],
                        ROOK_SEMIOPEN[1],
                        ROOK_SEMIOPEN[2],
                        weights,
                    )
            if (color == chess.WHITE and rank == 6) or (
                color == chess.BLACK and rank == 1
            ):
                score += mul * _interpolate(
                    ROOK_7TH[0], ROOK_7TH[1], ROOK_7TH[2], weights
                )
    return score


def _knights_score(board: chess.Board, weights: tuple[float, float, float]) -> int:
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
                        score += mul * _interpolate(
                            OUTPOST[0], OUTPOST[1], OUTPOST[2], weights
                        )
    return score


def evaluate(board: chess.Board) -> int:
    """
    Полная трёхфазная HCE оценка позиции с точки зрения белых.
    """
    term = _terminal_score(board)
    if term is not None:
        return term

    weights = calculate_phase(board)

    score = 0
    for pt, val in VALUES.items():
        score += val * len(board.pieces(pt, chess.WHITE))
        score -= val * len(board.pieces(pt, chess.BLACK))

    score += _pst_score(board, weights)
    score += _king_score(board, weights)
    score += _mobility_score(board, weights)
    score += _pawns_score(board, weights)
    score += _king_safety_score(board, weights)
    score += _bishop_pair_score(board, weights)
    score += _rooks_score(board, weights)
    score += _knights_score(board, weights)

    return score
