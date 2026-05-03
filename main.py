#!/usr/bin/env python3

"""
Точка входа в движок Dumbfish
"""

import sys
from game import Game
from uci import uci_loop

def main():
    sys.stdout.reconfigure(line_buffering=True)
    
    game = Game()
    uci_loop(game)


if __name__ == "__main__":
    main()