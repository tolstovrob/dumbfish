"""
Модуль поиска с итеративным углублением и альфа-бета отсечением
"""

import chess
from evaluation import evaluate
from tt import TranspositionTable, TTFlag


MVV_LVA_PRIORITY = {
    chess.PAWN: 1,
    chess.KNIGHT: 2,
    chess.BISHOP: 3,
    chess.ROOK: 4,
    chess.QUEEN: 5,
    chess.KING: 6,
}


def _order_moves(board: chess.Board, moves: list[chess.Move], 
                 tt_move: chess.Move | None = None) -> list[chess.Move]:
    """
    Сортировка ходов: TT-ход, затем взятия (MVV-LVA), затем тихие ходы.
    """
    def score(move: chess.Move) -> int:
        if tt_move is not None and move == tt_move:
            return 2_000_000
        
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                return 1_000_000 + MVV_LVA_PRIORITY[victim.piece_type] * 10 - MVV_LVA_PRIORITY[attacker.piece_type]
            return 1_000_000
        return 0

    return sorted(moves, key=score, reverse=True)


def _to_side_score(board: chess.Board) -> int:
    """Оценка с точки зрения того, чей сейчас ход."""
    score = evaluate(board)
    return score if board.turn == chess.WHITE else -score


def _quiescence(board: chess.Board, alpha: int, beta: int, tt: TranspositionTable) -> int:
    """
    Quiescence search с поддержкой TT.
    alpha/beta &mdash; с точки зрения игрока, чей ход.
    Возвращает оценку с его же точки зрения.
    """
    if board.is_game_over():
        return _to_side_score(board)
    
    hash_val = tt.get_hash(board)
    tt_entry = tt.probe(hash_val)
    
    if tt_entry is not None:
        if tt_entry.flag == TTFlag.EXACT:
            return tt_entry.score
        elif tt_entry.flag == TTFlag.ALPHA and tt_entry.score <= alpha:
            return tt_entry.score
        elif tt_entry.flag == TTFlag.BETA and tt_entry.score >= beta:
            return tt_entry.score

    in_check = board.is_check()

    if not in_check:
        stand_pat = _to_side_score(board)
        if stand_pat >= beta:
            tt.store(hash_val, 0, stand_pat, TTFlag.BETA, None)
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

    if in_check:
        moves = list(board.legal_moves)
    else:
        moves = [m for m in board.legal_moves if board.is_capture(m)]

    tt_best_move = tt_entry.best_move if tt_entry else None
    moves = _order_moves(board, moves, tt_move=tt_best_move)

    best_score = -100_000
    best_move = None

    for move in moves:
        board.push(move)
        score = -_quiescence(board, -beta, -alpha, tt)
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score >= beta:
            break
        
        if score > alpha:
            alpha = score

    flag = TTFlag.EXACT
    if best_score <= alpha:
        flag = TTFlag.ALPHA
    elif best_score >= beta:
        flag = TTFlag.BETA
    
    tt.store(hash_val, 0, best_score, flag, best_move)
    
    return best_score


def _negamax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    tt: TranspositionTable,
    ply: int = 0,
) -> tuple[int, chess.Move | None]:
    """
    Negamax с альфа-бета и TT.
    alpha/beta и результат &mdash; с точки зрения того, чей ход.
    """
    if board.is_game_over():
        return _to_side_score(board), None

    hash_val = tt.get_hash(board)
    tt_entry = tt.probe(hash_val)
    
    if (tt_entry is not None and 
        tt_entry.depth >= depth and
        tt_entry.hash == hash_val):
        
        if tt_entry.flag == TTFlag.EXACT:
            return tt_entry.score, tt_entry.best_move
        elif tt_entry.flag == TTFlag.ALPHA and tt_entry.score <= alpha:
            return tt_entry.score, tt_entry.best_move
        elif tt_entry.flag == TTFlag.BETA and tt_entry.score >= beta:
            return tt_entry.score, tt_entry.best_move

    if depth == 0:
        score = _quiescence(board, alpha, beta, tt)
        return score, None

    best_move = None
    best_score = -100_000
    original_alpha = alpha

    tt_best_move = tt_entry.best_move if tt_entry else None
    moves = _order_moves(board, list(board.legal_moves), tt_move=tt_best_move)

    for move in moves:
        board.push(move)
        score, _ = _negamax(board, depth - 1, -beta, -alpha, tt, ply + 1)
        score = -score
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break

    if best_score <= original_alpha:
        flag = TTFlag.ALPHA
    elif best_score >= beta:
        flag = TTFlag.BETA
    else:
        flag = TTFlag.EXACT

    tt.store(hash_val, depth, best_score, flag, best_move)

    return best_score, best_move



def search(board: chess.Board, max_depth: int, tt: TranspositionTable) -> chess.Move | None:
    """
    Итеративное углубление от 1 до max_depth.
    Возвращает лучший ход.
    """
    best_move = None

    for depth in range(1, max_depth + 1):
        _, move = _negamax(board, depth, -100_000, 100_000, tt)
        if move is not None:
            best_move = move
        
    return best_move