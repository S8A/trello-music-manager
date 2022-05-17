"""Utility functions."""
from typing import List

import os
from contextlib import contextmanager


@contextmanager
def cd(new_dir: str):
    """Context manager for changing the current working directory"""

    prev_dir = os.getcwd()
    os.chdir(os.path.expanduser(new_dir))
    try:
        yield
    finally:
        os.chdir(prev_dir)


def read_file_lines_stripped(filename: str) -> List[str]:
    """Extract the specified file's lines into a list after stripping them."""
    stripped_lines = []
    with open(filename) as f:
        for line in f:
            stripped_lines.append(line.strip())
    return stripped_lines
