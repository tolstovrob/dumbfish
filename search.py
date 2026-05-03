"""
Модуль поиска с итеративным углублением и альфа-бета отсечением
"""

import chess
from evaluation import evaluate


MVV_LVA_PRIORITY = {
    chess.PAWN: 1,
    chess.KNIGHT: 2,
    chess.BISHOP: 3,
    chess.ROOK: 4,
    chess.QUEEN: 5,
    chess.KING: 6,
}


def _order_moves(board: chess.Board, moves: list[chess.Move]) -> list[chess.Move]:
    """Сортировка: взятия (MVV-LVA) вперёд, затем тихие ходы."""

    def score(move: chess.Move) -> int:
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                return 1000 + MVV_LVA_PRIORITY[victim.piece_type] * 10 - MVV_LVA_PRIORITY[attacker.piece_type]
            return 1000
        return 0

    return sorted(moves, key=score, reverse=True)


def _to_side_score(board: chess.Board) -> int:
    """Оценка с точки зрения того, чей сейчас ход."""
    score = evaluate(board)
    return score if board.turn == chess.WHITE else -score


def _quiescence(board: chess.Board, alpha: int, beta: int) -> int:
    """
    Quiescence search. alpha/beta — с точки зрения игрока, чей ход.
    Возвращает оценку с его же точки зрения.
    """
    if board.is_game_over():
        return _to_side_score(board)

    in_check = board.is_check()

    if not in_check:
        stand_pat = _to_side_score(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

    if in_check:
        moves = list(board.legal_moves)
    else:
        moves = [m for m in board.legal_moves if board.is_capture(m)]

    moves = _order_moves(board, moves)

    for move in moves:
        board.push(move)
        score = -_quiescence(board, -beta, -alpha)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def _negamax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
) -> tuple[int, chess.Move | None]:
    """
    Negamax с альфа-бета.
    alpha/beta и результат — с точки зрения того, чей ход.
    """
    if board.is_game_over():
        return _to_side_score(board), None

    if depth == 0:
        return _quiescence(board, alpha, beta), None

    best_move = None
    best_score = -100_000

    moves = _order_moves(board, list(board.legal_moves))

    for move in moves:
        board.push(move)
        score, _ = _negamax(board, depth - 1, -beta, -alpha)
        score = -score
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break

    return best_score, best_move


def search(board: chess.Board, max_depth: int) -> chess.Move | None:
    """
    Итеративное углубление от 1 до max_depth.
    Возвращает лучший ход.
    """
    best_move = None

    for depth in range(1, max_depth + 1):
        _, move = _negamax(board, depth, -100_000, 100_000)
        if move is not None:
            best_move = move

    return best_move