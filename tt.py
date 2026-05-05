"""
Транспозиционная позиция с Zobrist-хешированием
"""

import chess
import chess.polyglot
from enum import Enum


class TTFlag(Enum):
    EXACT = 0
    ALPHA = 1
    BETA = 2


class TTEntry:
    __slots__ = ['hash', 'depth', 'score', 'flag', 'best_move']

    def __init__(self, hash: int, depth: int, score: int,
                 flag: TTFlag, best_move: chess.Move | None):
        self.hash = hash
        self.depth = depth
        self.score = score
        self.flag = flag
        self.best_move = best_move

    
class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        """
        size_mb - размер таблицы в мегабайтах.
        Каждая запись занимает ~32 байта.
        """

        self.size = 1
        while self.size < (size_mb * 1024 * 1024) // 32:
            self.size <<= 1
        self.size -= 1

        self.table: list[TTEntry | None] = [None] * (self.size + 1)
        self.hits = 0
        self.misses = 0
        self.writes = 0

    
    def __len__(self):
        return sum(1 for entry in self.table if entry is not None)
    

    def probe(self, hash_val: int) -> TTEntry | None:
        """Поиск позиции в таблице. Возвращает запись с тем же хешем или None."""
        
        index = hash_val & self.size
        entry = self.table[index]
        
        if entry is not None and entry.hash == hash_val:
            self.hits += 1
            return entry
        
        self.misses += 1        
        return None
    

    def store(self, hash_val: int, depth: int, score: int,
              flag: TTFlag, best_move: chess.Move | None) -> None:
        """
        Сохранение позиции в таблице.
        Всегда замещает запись если:
        - Ячейка пуста
        - Новая глубина >= старой
        - Хеш отличается (коллизия)
        """
        
        index = hash_val & self.size
        existing = self.table[index]

        if existing is None \
           or depth >= existing.depth \
           or existing.hash != hash_val:
            self.table[index] = TTEntry(hash_val, depth, score, flag, best_move)
            self.writes += 1

    
    def get_hash(self, board: chess.Board) -> int:
        """Возвращает хеш для позиции в формате Zobrist."""
        return chess.polyglot.zobrist_hash(board)
    

    def clear(self) -> None:
        self.table = [None] * (self.size + 1)
        self.hits = 0
        self.misses = 0
        self.writes = 0

    
    def get_stats(self) -> dict:
        """Статистика использования таблицы."""
        total_probes = self.hits + (self.misses if self.writes > 0 else 0)
        hit_rate = (self.hits / total_probes * 100) if total_probes > 0 else 0
        load_factor = len(self) / (self.size + 1) * 100

        return {
            'size': self.size + 1,
            'entries': len(self),
            'hits': self.hits,
            'misses': self.misses,
            'writes': self.writes,
            'hit_rate': f"{hit_rate:.1f}%",
            'load_factor': f"{load_factor:.1f}%"
        }