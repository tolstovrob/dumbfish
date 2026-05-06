"""
UCI-протокол движка
"""

import sys
from config import CONFIG
from game import Game
from search import search


class QuitException(Exception):
    """Сигнал завершить UCI-цикл."""


def handle_uci(args: list[str], game: Game) -> None:
    print(f"id name {CONFIG.NAME}")
    print(f"id author {CONFIG.AUTHOR}")
    print("uciok")


def handle_isready(args: list[str], game: Game) -> None:
    print("readyok")


def handle_ucinewgame(args: list[str], game: Game) -> None:
    game.reset()


def handle_position(args: list[str], game: Game) -> None:
    if not args:
        return

    if args[0] == "startpos":
        game.reset()
        moves_start_idx = 1
    elif args[0] == "fen":
        fen_parts = []
        i = 1
        while i < len(args) and len(fen_parts) < 6:
            fen_parts.append(args[i])
            i += 1
        fen = " ".join(fen_parts)
        if not game.set_fen(fen):
            return
        moves_start_idx = i
    else:
        return

    if moves_start_idx < len(args) and args[moves_start_idx] == "moves":
        game.apply_moves(args[moves_start_idx + 1:])


def handle_go(args: list[str], game: Game) -> None:
    depth = 8
    if "depth" in args:
        idx = args.index("depth")
        if idx + 1 < len(args):
            try:
                depth = int(args[idx + 1])
            except ValueError:
                pass

    best_move = search(game.get_board(), depth, game.get_tt())

    if best_move is not None:
        print(f"bestmove {best_move}")
    else:
        print("bestmove 0000")


def handle_quit(args: list[str], game: Game) -> None:
    raise QuitException()


DISPATCH = {
    "uci": handle_uci,
    "isready": handle_isready,
    "ucinewgame": handle_ucinewgame,
    "position": handle_position,
    "go": handle_go,
    "quit": handle_quit,
}


def uci_loop(game: Game) -> None:
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
                handler(args, game)
            except QuitException:
                break

        sys.stdout.flush()