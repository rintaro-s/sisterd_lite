"""
systerd entry point for direct execution.
Usage: python3 -m systerd
"""

import sys
from .app import main

if __name__ == "__main__":
    sys.exit(main())
