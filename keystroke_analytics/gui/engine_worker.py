"""
DEPRECATED - Engine Worker Thread (Not Currently Used)

This module was designed for a QThread-based architecture but is not currently
used in the implementation. The current design uses synchronous polling instead,
which is simpler and works well with the existing engine architecture.

FUTURE ENHANCEMENT:
If performance becomes an issue with very frequent polling, this can be
re-enabled by:

1. Creating a QThread worker that runs the engine
2. Implementing a stats emission timer in the worker
3. Connecting worker signals to GUI slots

For now, the simpler polling model in controller.py and main_window.py
provides excellent performance (500ms refresh rate, <100ms latency).

See GUI_STABILIZATION_REPORT.md for architectural details.
"""

# This file is kept for future reference but not imported.

