"""
Игровое состояние движка. Абстракция над chess.Board
"""

import chess

class Game:
    """Хранит текущую доску и операции над ней"""
    
    def __init__(self) -> None:
        self.board = chess.Board()

    
    def reset(self) -> None:
        """Сброс в начальную позицию"""
        self.board = chess.Board()


    def set_fen(self, fen: str) -> bool:
        """Установить позицию в формате FEN. Вернуть False при ошибке"""
        try:
            self.board = chess.Board(fen)
            return True
        except ValueError:
            return False
    
    
    def apply_moves(self, uci_moves: list[str]) -> None:
        """
        Применить ходы UCI к текущей позиции.
        Невоззможные ходы игнорируются с остановкой
        """
        for move in uci_moves:
            try:
                self.board.push_uci(move)
            except ValueError:
                break
    

    def get_board(self) -> chess.Board:
        """Получить текущую доску"""
        return self.board