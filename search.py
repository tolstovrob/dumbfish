"""
Иодуль поиска с итеративным углублением и альфа-бета отсечением
"""

import chess
from evaluation import evaluate
from config import CONFIG


def search(board: chess.Board, max_depth: int) -> chess.Board:
    """
    Поиск с итеративным углублением от 1 до max_depth. Возвращает лучший ход
    """

    best_move = None

    for depth in range(1, max_depth + 1):
        score, move = _alpha_beta(board, depth, -100_000, 100_000)
        if move is not None:
            best_move = move
        # TODO: break on forced mate
            
    return best_move


def _alpha_beta(board: chess.Board, depth: int, alpha: int, beta: int) -> tuple[int, chess.Move | None]:
    if board.is_game_over() or depth == 0:
        return evaluate(board), None

    best_move = None
    legal_moves = list(board.legal_moves)

    if board.turn == chess.WHITE:
        max_score = -100_000
        for move in legal_moves:
            board.push(move)
            score, _ = _alpha_beta(board, depth - 1, alpha, beta)
            board.pop()

            if score > max_score:
                max_score = score
                best_move = move
                
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return max_score, best_move
    else:
        min_score = 100_000
        for move in legal_moves:
            board.push(move)
            score, _ = _alpha_beta(board, depth - 1, alpha, beta)
            board.pop()

            if score < min_score:
                min_score = score
                best_move = move
                
            beta = min(beta, score)
            if beta <= alpha:
                break
        return min_score, best_move