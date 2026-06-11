"""
Поиск с Principal Variation Search и альфа-бета отсечением.

Реализованы следующие оптимизации:
  - Principal Variation Search (PVS) - основной алгоритм
  - Null-move pruning - пропуск хода для быстрого отсечения
  - Late Move Reductions (LMR) - уменьшение глубины для неперспективных ходов
  - Futility pruning - отсечение заведомо слабых ходов на малой глубине
  - Quiescence search - поиск тихих ходов (взятий) до спокойной позиции
  - Killer heuristic - два лучших тихих хода на каждой глубине
  - History heuristic - таблица 64x64 для сортировки тихих ходов
  - Transposition table - кеширование просчитанных позиций

Все оценки с точки зрения игрока, чей сейчас ход.
"""

import chess
import time
from score import evaluate
from tt import TranspositionTable, TTFlag

MATE_SCORE = 100_000
MAX_DEPTH = 128
HISTORY_MAX = 16384

# Эвристика истории ходов
history_table = [[0] * 64 for _ in range(64)]

# Эвристика тихих ходов
killer_moves = [[None, None] for _ in range(MAX_DEPTH)]

# Приоритеты фигур MVV-LVA
MVV_LVA = {
    chess.PAWN: 1,
    chess.KNIGHT: 2,
    chess.BISHOP: 3,
    chess.ROOK: 4,
    chess.QUEEN: 5,
    chess.KING: 6,
}

_nodes = 0
_start_time = 0.0


def _reset_stats():
    """Сброс счётчиков перед новым поиском."""
    global _nodes, _start_time
    _nodes = 0
    _start_time = time.time()


def _get_stats():
    """Получение текущей статистики."""
    elapsed = max(time.time() - _start_time, 0.001)
    nps = int(_nodes / elapsed)
    return _nodes, int(elapsed * 1000), nps


def _see_capture(board: chess.Board, move: chess.Move) -> int:
    """
    Оценка Static Exchange Evaluation для взятия.

    Оценивает выгодность взятия по принципу MVV-LVA:
    чем ценнее жертва и чем дешевле атакующий, тем выше оценка.
    """
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim is None or attacker is None:
        return 0
    return MVV_LVA[victim.piece_type] * 10 - MVV_LVA[attacker.piece_type]


def _move_value(
    board: chess.Board, move: chess.Move, tt_move: chess.Move | None, ply: int
) -> int:
    """
    Оценка хода для сортировки. Чем выше значение, тем раньше ход будет проверен.

    Приоритеты (от высшего к низшему):
      1. Ход из транспозиционной таблицы (10 000 000)
      2. Взятия по MVV-LVA (1 000 000 + оценка SEE)
      3. Превращения (900 000 + ценность фигуры)
      4. Первый тихий ход (800 000)
      5. Второй тихий ход (700 000)
      6. History heuristic (0..16384)

    Хороший ход в начале вызывает бета-отсечение и экономит перебор остальных
    ходов.
    """

    if tt_move is not None and move == tt_move:
        return 10_000_000

    if board.is_capture(move):
        return 1_000_000 + _see_capture(board, move)

    if move.promotion:
        return 900_000 + MVV_LVA[move.promotion]

    if move == killer_moves[ply][0]:
        return 800_000
    if move == killer_moves[ply][1]:
        return 700_000

    return history_table[move.from_square][move.to_square]


def _order_moves(
    board: chess.Board, moves: list[chess.Move], tt_move: chess.Move | None, ply: int
) -> list[chess.Move]:
    """
    Сортировка ходов по убыванию их оценочной ценности.
    """

    scored = [(_move_value(board, m, tt_move, ply), m) for m in moves]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [m for _, m in scored]


def _to_side_score(board: chess.Board) -> int:
    """
    Преобразует оценку из абсолютной (относительно белых) в относительную.
    """

    score = evaluate(board)
    return score if board.turn == chess.WHITE else -score


def _is_quiet(board: chess.Board, move: chess.Move) -> bool:
    """
    Проверяет, является ли ход тихим (не взятие, не шах, не превращение).

    Тихие ходы - кандидаты для киллеров и history heuristic.
    """

    if board.is_capture(move) or move.promotion:
        return False
    board.push(move)
    in_check = board.is_check()
    board.pop()
    return not in_check


def _update_killers(move: chess.Move, ply: int) -> None:
    """
    Обновляет эвристику тихих ходов для текущей глубины.
    """

    if move == killer_moves[ply][0]:
        return
    killer_moves[ply][1] = killer_moves[ply][0]
    killer_moves[ply][0] = move


def _update_history(move: chess.Move, depth: int) -> None:
    """
    Обновляет эвристику истории ходов для тихого хода, вызвавшего отсечение.

    Бонус пропорционален квадрату глубины (ход на большой глубине ценнее).
    Используется плавное обновление: val += bonus - val * bonus / MAX
    чтобы избежать переполнения и резких скачков.
    """

    bonus = min(depth * depth, 400)
    val = history_table[move.from_square][move.to_square]
    history_table[move.from_square][move.to_square] = (
        val + bonus - (val * bonus) // HISTORY_MAX
    )


def _quiescence(
    board: chess.Board, alpha: int, beta: int, tt: TranspositionTable
) -> int:
    """
    Поиск в глубину только взятий до достижения "спокойной" позиции.

    Аргументы:
      board - текущая позиция
      alpha - нижняя граница (лучшее, что можем гарантировать)
      beta  - верхняя граница (лучшее, что соперник нам позволит)
      tt    - транспозиционная таблица

    Возвращает оценку с точки зрения игрока, чей ход.
    """

    global _nodes
    _nodes += 1

    if board.is_game_over():
        return _to_side_score(board)

    hash_val = tt.get_hash(board)
    tt_entry = tt.probe(hash_val)
    if tt_entry is not None:
        if tt_entry.flag == TTFlag.EXACT:
            return tt_entry.score
        if tt_entry.flag == TTFlag.ALPHA and tt_entry.score <= alpha:
            return tt_entry.score
        if tt_entry.flag == TTFlag.BETA and tt_entry.score >= beta:
            return tt_entry.score

    stand_pat = _to_side_score(board)
    if stand_pat >= beta:
        tt.store(hash_val, 0, stand_pat, TTFlag.BETA, None)
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    in_check = board.is_check()
    if in_check:
        moves = list(board.legal_moves)
    else:
        moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]

    if not in_check:
        delta = 200
        moves = [
            m for m in moves if stand_pat + _see_material(board, m) + delta >= alpha
        ]

    tt_best_move = tt_entry.best_move if tt_entry else None
    moves = _order_moves(board, moves, tt_best_move, 0)

    best_score = stand_pat
    best_move = None

    for move in moves:
        board.push(move)
        score = -_quiescence(board, -beta, -alpha, tt)
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score >= beta:
            if not board.is_capture(move):
                _update_killers(move, 0)
            tt.store(hash_val, 0, score, TTFlag.BETA, move)
            return beta

        if score > alpha:
            alpha = score

    flag = TTFlag.EXACT if best_score > stand_pat else TTFlag.ALPHA
    tt.store(hash_val, 0, best_score, flag, best_move)
    return best_score


def _see_material(board: chess.Board, move: chess.Move) -> int:
    """
    Приблизительная материальная ценность хода для delta pruning.
    Возвращает 0 для тихих ходов, ценность жертвы для взятий.
    """

    if not board.is_capture(move) and not move.promotion:
        return 0
    victim = board.piece_at(move.to_square)
    if victim:
        return MVV_LVA[victim.piece_type] * 100
    return 0


def _pv_search(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    tt: TranspositionTable,
    ply: int,
    can_null: bool,
    pv_line: list[chess.Move] | None = None,
) -> tuple[int, chess.Move | None]:
    """
    Principal Variation Search с альфа-бета отсечением.

    Аргументы:
      board    - текущая позиция
      depth    - оставшаяся глубина поиска
      alpha    - нижняя граница
      beta     - верхняя граница
      tt       - транспозиционная таблица
      ply      - текущая глубина от корня (для киллеров)
      can_null - можно ли применять null-move pruning
      pv_line  - список для сбора PV (изменяется на месте)

    Возвращает кортеж с оценкой и лучшим ходом.
    """

    global _nodes
    _nodes += 1

    if board.is_game_over():
        return _to_side_score(board), None

    hash_val = tt.get_hash(board)
    tt_entry = tt.probe(hash_val)

    if tt_entry is not None and tt_entry.depth >= depth:
        if tt_entry.flag == TTFlag.EXACT:
            return tt_entry.score, tt_entry.best_move
        if tt_entry.flag == TTFlag.ALPHA and tt_entry.score <= alpha:
            return tt_entry.score, tt_entry.best_move
        if tt_entry.flag == TTFlag.BETA and tt_entry.score >= beta:
            return tt_entry.score, tt_entry.best_move

    if depth <= 0:
        score = _quiescence(board, alpha, beta, tt)
        return score, None

    # Null-move pruning
    if can_null and depth >= 3 and not board.is_check():
        R = 3 + depth // 6
        board.push(chess.Move.null())
        score, _ = _pv_search(
            board, depth - R - 1, -beta, -beta + 1, tt, ply + 1, False
        )
        board.pop()
        score = -score
        if score >= beta:
            return beta, None

    # Futility pruning
    if depth <= 3 and not board.is_check():
        stand_pat = _to_side_score(board)
        if stand_pat + 200 * depth <= alpha:
            score = _quiescence(board, alpha, beta, tt)
            return score, None

    tt_best_move = tt_entry.best_move if tt_entry else None
    moves = list(board.legal_moves)

    if not moves:
        if board.is_check():
            return -MATE_SCORE + ply, None
        return 0, None

    moves = _order_moves(board, moves, tt_best_move, ply)

    best_move = moves[0]
    best_score = -MATE_SCORE
    original_alpha = alpha
    moves_searched = 0

    local_pv = []

    for i, move in enumerate(moves):
        board.push(move)

        # Late Move Reductions
        if moves_searched >= 4 and depth >= 3 and _is_quiet(board, move):
            R = 1 + depth // 4 + moves_searched // 8
            new_depth = max(1, depth - R)
            child_pv = []
            score, _ = _pv_search(
                board, new_depth, -alpha - 1, -alpha, tt, ply + 1, True, child_pv
            )
            score = -score
            if score > alpha:
                child_pv = []
                score, _ = _pv_search(
                    board, depth - 1, -beta, -alpha, tt, ply + 1, True, child_pv
                )
                score = -score
        else:
            child_pv = []
            if moves_searched == 0:
                score, _ = _pv_search(
                    board, depth - 1, -beta, -alpha, tt, ply + 1, True, child_pv
                )
            else:
                score, _ = _pv_search(
                    board, depth - 1, -alpha - 1, -alpha, tt, ply + 1, True, child_pv
                )
                if score > alpha and score < beta:
                    child_pv = []
                    score, _ = _pv_search(
                        board, depth - 1, -beta, -alpha, tt, ply + 1, True, child_pv
                    )
            score = -score

        board.pop()
        moves_searched += 1

        if score > best_score:
            best_score = score
            best_move = move
            local_pv = [move] + child_pv

        if score > alpha:
            alpha = score
            if score >= beta:
                if _is_quiet(board, move):
                    _update_killers(move, ply)
                    _update_history(move, depth)
                break

    if pv_line is not None and local_pv:
        pv_line.clear()
        pv_line.extend(local_pv)

    if best_score <= original_alpha:
        flag = TTFlag.ALPHA
    elif best_score >= beta:
        flag = TTFlag.BETA
    else:
        flag = TTFlag.EXACT

    tt.store(hash_val, depth, best_score, flag, best_move)
    return best_score, best_move


def search(
    board: chess.Board, max_depth: int, tt: TranspositionTable
) -> tuple[chess.Move | None, list[dict]]:
    """
    Основная функция поиска с итеративным углублением.

    Аргументы:
      board     - текущая позиция
      max_depth - максимальная глубина
      tt        - транспозиционная таблица

    Возвращает кортеж (лучший ход, список info-словарей для каждой итерации).
    Каждый info-словарь содержит ключи:
      - depth, score, nodes, time, nps, pv
    """

    _reset_stats()

    for i in range(MAX_DEPTH):
        killer_moves[i][0] = None
        killer_moves[i][1] = None

    best_move = None
    info_list = []

    for depth in range(1, max_depth + 1):
        pv_line = []
        _, move = _pv_search(
            board, depth, -MATE_SCORE, MATE_SCORE, tt, 0, True, pv_line
        )
        if move is not None:
            best_move = move

        nodes, time_ms, nps = _get_stats()

        info = {
            "depth": depth,
            "score": _pv_search(board, depth, -MATE_SCORE, MATE_SCORE, tt, 0, True)[0],
            "nodes": nodes,
            "time": time_ms,
            "nps": nps,
            "pv": pv_line if pv_line else [best_move] if best_move else [],
        }
        info_list.append(info)

    return best_move, info_list
