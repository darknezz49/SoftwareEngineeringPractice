"""Presentation layer: the POS user interfaces.

Two interchangeable views sit on top of the same application layer:

* :mod:`pos.presentation.gui` - the Tkinter graphical terminal (default);
* :mod:`pos.presentation.terminal` - the text-mode terminal (``--terminal``).
"""
from .gui import POSWindow, launch
from .terminal import TerminalPOS, run_terminal

__all__ = ["POSWindow", "launch", "TerminalPOS", "run_terminal"]
