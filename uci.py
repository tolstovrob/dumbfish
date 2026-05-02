"""
UCI-протокол движка
"""

import sys
from config import CONFIG


class QuitException(Exception):
    """Сигнал завершить UCI-цикл"""


def handle_uci(args: list[str]) -> None:
    print(f"id name {CONFIG.NAME}")
    print(f"id author {CONFIG.AUTHOR}")
    print(f"uciok")


def handle_isready(args: list[str]) -> None:
    print("readyok")


def handle_ucinewgame(args: list[str]) -> None:
    pass


def handle_quit(args: list[str]) -> None:
    raise QuitException()


DISPATCH = {
    "uci": handle_uci,
    "isready": handle_isready,
    "ucinewgame": handle_ucinewgame,
    "quit": handle_quit,
}

def uci_loop() -> None:
    """
    Главный цикл UCI-протокола
    """

    while True:
        try:
            line = sys.stdin.readline()
        except EOFError:
            break
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        command, *args = line.split()
        handler = DISPATCH.get(command)

        if handler is not None:
            try:
                handler(args)
            except QuitException:
                break

        sys.stdout.flush()
