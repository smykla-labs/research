"""Package entry point for running as module: python -m scripts."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
