"""
Конфигурация движка Dumbfish
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    NAME = "Dumbfish"
    AUTHOR = "tolstovrob"


CONFIG = Config()