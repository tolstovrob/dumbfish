"""
UCI-протокол движка
"""

import sys
import chess
from config import CONFIG
from game import Game
from search import search


class QuitException(Exception):
    """Сигнал завершить UCI-цикл."""


def _format_score(score: int) -> str:
    """
    Форматирует оценку в UCI-формат.
    
    Для матовых оценок: mate N (где N - ходы до мата)
    Для обычных оценок: cp S (сантипешки, оценка в centipawns)
    
    Внутренняя оценка: положительная = хорошо для белых
    UCI: положительная = хорошо для текущего игрока
    """
    MATE_THRESHOLD = 100_000

    if abs(score) >= MATE_THRESHOLD:
        if score > 0:
            mate_in = (100_000 - score + 1) // 2
        else:
            mate_in = (100_000 + score + 1) // 2
        return f"mate {mate_in}"
    else:
        return f"cp {score}"


def _format_pv(pv_line: list) -> str:
    """Форматирует PV линию в UCI-строку."""
    if not pv_line:
        return ""
    return " ".join(move.uci() if hasattr(move, 'uci') else str(move) 
                    for move in pv_line)


def _print_info(info: dict, board_turn: chess.Color) -> None:
    """
    Выводит info-строку в UCI-формате.
    
    Формат: info depth N score [cp S | mate N] nodes N time N nps N pv M1 M2 ...
    
    Оценка score преобразуется: внутренняя всегда с точки зрения белых,
    UCI требует с точки зрения текущего игрока.
    """
    score = info['score']
    if board_turn == chess.BLACK:
        score = -score

    parts = [
        f"depth {info['depth']}",
        f"score {_format_score(score)}",
        f"nodes {info['nodes']}",
        f"time {info['time']}",
        f"nps {info['nps']}",
    ]

    pv_str = _format_pv(info.get('pv', []))
    if pv_str:
        parts.append(f"pv {pv_str}")

    print("info " + " ".join(parts))


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
    depth = 16
    if "depth" in args:
        idx = args.index("depth")
        if idx + 1 < len(args):
            try:
                depth = int(args[idx + 1])
            except ValueError:
                pass

    if "infinite" in args:
        return

    best_move, info_list = search(game.get_board(), depth, game.get_tt())
    
    for info in info_list:
        _print_info(info, game.get_board().turn)
    
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