"""
Вычисление признаков NNUE из шахматной позиции.

Признаки: 768 = 64 клетки * (6 белых + 6 чёрных фигур)
Для каждой клетки и каждого типа фигуры: 1 если фигура стоит, иначе 0

Инкрементальное обновление: при добавлении/удалении фигуры
обновляется соответствующий элемент вектора признаков.
"""

import chess
import numpy as np


PIECE_TO_INDEX = {
    (chess.WHITE, chess.PAWN): 0,
    (chess.WHITE, chess.KNIGHT): 1,
    (chess.WHITE, chess.BISHOP): 2,
    (chess.WHITE, chess.ROOK): 3,
    (chess.WHITE, chess.QUEEN): 4,
    (chess.WHITE, chess.KING): 5,
    (chess.BLACK, chess.PAWN): 6,
    (chess.BLACK, chess.KNIGHT): 7,
    (chess.BLACK, chess.BISHOP): 8,
    (chess.BLACK, chess.ROOK): 9,
    (chess.BLACK, chess.QUEEN): 10,
    (chess.BLACK, chess.KING): 11,
}

NUM_FEATURES = 768


def _square_index(square: int, piece_type: int, color: chess.Color) -> int:
    """
    Возвращает индекс в векторе признаков для данной фигуры на данной клетке.
    """
    piece_idx = PIECE_TO_INDEX[(color, piece_type)]
    return piece_idx * 64 + square


def compute_features(board: chess.Board) -> np.ndarray:
    """
    Полное вычисление вектора признаков из позиции.
    
    Возвращает numpy массив формы (768,) с типом int8 (0 или 1).
    """
    features = np.zeros(NUM_FEATURES, dtype=np.int8)
    
    for color in [chess.WHITE, chess.BLACK]:
        for piece_type in chess.PIECE_TYPES:
            squares = board.pieces(piece_type, color)
            piece_idx = PIECE_TO_INDEX[(color, piece_type)]
            for sq in squares:
                features[piece_idx * 64 + sq] = 1
                
    return features


def get_active_features(board: chess.Board) -> tuple[np.ndarray, np.ndarray]:
    """
    Возвращает индексы активных признаков и их значения (всегда 1).
    Более эффективно для инференса — работаем с разреженным представлением.
    
    Returns:
        indices: np.ndarray[int32] — индексы ненулевых признаков
        values: np.ndarray[int8] — значения (все единицы)
    """
    indices = []
    
    for color in [chess.WHITE, chess.BLACK]:
        for piece_type in chess.PIECE_TYPES:
            squares = board.pieces(piece_type, color)
            piece_idx = PIECE_TO_INDEX[(color, piece_type)]
            for sq in squares:
                indices.append(piece_idx * 64 + sq)
                
    return np.array(indices, dtype=np.int32), np.ones(len(indices), dtype=np.int8)


def update_features(
    board: chess.Board,
    move: chess.Move,
    current_features: np.ndarray
) -> np.ndarray:
    """
    Инкрементальное обновление признаков после хода.
    
    Args:
        board: доска ДО хода
        move: сделанный ход
        current_features: текущий вектор признаков
    
    Returns:
        Тот же массив current_features с обновлёнными значениями
    """
    from_sq = move.from_square
    to_sq = move.to_square
    
    piece = board.piece_at(from_sq)
    if piece is None:
        return current_features
    
    idx = _square_index(from_sq, piece.piece_type, piece.color)
    current_features[idx] = 0
    
    captured = board.piece_at(to_sq)
    if captured:
        idx = _square_index(to_sq, captured.piece_type, captured.color)
        current_features[idx] = 0
    
    promotion = move.promotion
    final_piece_type = promotion if promotion else piece.piece_type
    idx = _square_index(to_sq, final_piece_type, piece.color)
    current_features[idx] = 1
    
    if move.from_square == chess.E1 and move.to_square == chess.G1:
        current_features[_square_index(chess.H1, chess.ROOK, chess.WHITE)] = 0
        current_features[_square_index(chess.F1, chess.ROOK, chess.WHITE)] = 1
    elif move.from_square == chess.E1 and move.to_square == chess.C1:
        current_features[_square_index(chess.A1, chess.ROOK, chess.WHITE)] = 0
        current_features[_square_index(chess.D1, chess.ROOK, chess.WHITE)] = 1
    elif move.from_square == chess.E8 and move.to_square == chess.G8:
        current_features[_square_index(chess.H8, chess.ROOK, chess.BLACK)] = 0
        current_features[_square_index(chess.F8, chess.ROOK, chess.BLACK)] = 1
    elif move.from_square == chess.E8 and move.to_square == chess.C8:
        current_features[_square_index(chess.A8, chess.ROOK, chess.BLACK)] = 0
        current_features[_square_index(chess.D8, chess.ROOK, chess.BLACK)] = 1
    
    if piece.piece_type == chess.PAWN and to_sq == board.ep_square:
        captured_rank = 3 if piece.color == chess.WHITE else 4
        captured_sq = chess.square(chess.square_file(to_sq), captured_rank)
        captured_color = chess.BLACK if piece.color == chess.WHITE else chess.WHITE
        idx = _square_index(captured_sq, chess.PAWN, captured_color)
        current_features[idx] = 0
    
    return current_features