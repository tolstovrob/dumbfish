#!/usr/bin/env python3

"""
Точка входа в движок Dumbfish
"""

import sys
from uci import uci_loop


def main():
    sys.stdout.reconfigure(line_buffering=True)
    uci_loop()


if __name__ == "__main__":
    main()