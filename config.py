"""
Конфигурация движка
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    NAME = "Dumbfish"
    AUTHOR = "tolstovrob"
    DEFAULT_DEPTH = 6


CONFIG = Config()
