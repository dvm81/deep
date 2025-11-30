"""Verbose logging utilities for the research system."""

import time
from typing import Optional, Dict, Any
from datetime import datetime


# Global verbose flag - controlled by main.py
VERBOSE = False


def set_verbose(enabled: bool):
    """Enable or disable verbose logging.

    Args:
        enabled: Whether to enable verbose output
    """
    global VERBOSE
    VERBOSE = enabled


def is_verbose() -> bool:
    """Check if verbose logging is enabled."""
    return VERBOSE


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for colored terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Emojis for visual indicators
    ROCKET = "🚀"
    CHECK = "✓"
    CROSS = "✗"
    WARNING = "⚠️"
    INFO = "ℹ️"
    SEARCH = "🔍"
    ROBOT = "🤖"
    WRITE = "📝"
    SEND = "📤"
    RECEIVE = "📥"
    LINK = "🔗"
    TARGET = "🎯"
    BRAIN = "🧠"
    CLOCK = "⏰"
    CHART = "📊"
    FILE = "📁"
    CELEBRATE = "🎉"
    BOLT = "⚡"
    THINKING = "💭"
    CONFIG = "📋"
    GLOBE = "🌐"


def log_header(title: str, level: int = 1):
    """Print a section header.

    Args:
        title: Header title
        level: Header level (1=main, 2=sub)
    """
    if level == 1:
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{title}{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    else:
        print(f"\n{Colors.BRIGHT_YELLOW}{title}{Colors.RESET}")
        print(f"{Colors.DIM}{'-'*len(title)}{Colors.RESET}")


def log_phase(phase_num: int, phase_name: str):
    """Log a major phase transition.

    Args:
        phase_num: Phase number (1, 2, 3)
        phase_name: Phase name
    """
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLT} {Colors.BOLD}{Colors.BRIGHT_MAGENTA}PHASE {phase_num}: {phase_name}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")


def log_step(step: str, substeps: Optional[list] = None, emoji: str = ""):
    """Log a processing step.

    Args:
        step: Step description
        substeps: Optional list of substeps
        emoji: Optional emoji prefix
    """
    prefix = f"{emoji} " if emoji else ""
    print(f"{prefix}{Colors.BOLD}{step}{Colors.RESET}")

    if substeps:
        for substep in substeps:
            print(f"   {Colors.DIM}├─{Colors.RESET} {substep}")


def log_info(message: str, indent: int = 0):
    """Log informational message.

    Args:
        message: Message to log
        indent: Indentation level
    """
    prefix = "   " * indent
    print(f"{prefix}{Colors.INFO} {message}")


def log_success(message: str, indent: int = 0):
    """Log success message.

    Args:
        message: Message to log
        indent: Indentation level
    """
    prefix = "   " * indent
    print(f"{prefix}{Colors.GREEN}{Colors.CHECK} {message}{Colors.RESET}")


def log_warning(message: str, indent: int = 0):
    """Log warning message.

    Args:
        message: Message to log
        indent: Indentation level
    """
    prefix = "   " * indent
    print(f"{prefix}{Colors.YELLOW}{Colors.WARNING} {message}{Colors.RESET}")


def log_error(message: str, indent: int = 0):
    """Log error message.

    Args:
        message: Message to log
        indent: Indentation level
    """
    prefix = "   " * indent
    print(f"{prefix}{Colors.RED}{Colors.CROSS} {message}{Colors.RESET}")


def log_verbose(message: str, indent: int = 0):
    """Log verbose debug message (only if verbose mode enabled).

    Args:
        message: Message to log
        indent: Indentation level
    """
    if not VERBOSE:
        return

    prefix = "   " * indent
    print(f"{prefix}{Colors.DIM}{message}{Colors.RESET}")


def log_llm_call(
    purpose: str,
    prompt_preview: Optional[str] = None,
    response_preview: Optional[str] = None,
    model: str = "GPT-4.1",
    truncate: int = 500
):
    """Log an LLM API call with prompt/response previews.

    Args:
        purpose: What this LLM call is for
        prompt_preview: Optional prompt preview (will be truncated)
        response_preview: Optional response preview (will be truncated)
        model: Model name
        truncate: Max characters to show
    """
    if not VERBOSE:
        return

    print(f"   {Colors.ROBOT} {Colors.BOLD}AI Call:{Colors.RESET} {purpose}")
    print(f"      {Colors.DIM}Model: {model}{Colors.RESET}")

    if prompt_preview:
        truncated = prompt_preview[:truncate] + "..." if len(prompt_preview) > truncate else prompt_preview
        print(f"      {Colors.SEND} {Colors.DIM}Prompt Preview ({len(prompt_preview)} chars):{Colors.RESET}")
        for line in truncated.split('\n')[:5]:  # Max 5 lines
            print(f"         {Colors.DIM}{line}{Colors.RESET}")

    if response_preview:
        truncated = response_preview[:truncate] + "..." if len(response_preview) > truncate else response_preview
        print(f"      {Colors.RECEIVE} {Colors.DIM}Response Preview ({len(response_preview)} chars):{Colors.RESET}")
        for line in truncated.split('\n')[:5]:  # Max 5 lines
            print(f"         {Colors.DIM}{line}{Colors.RESET}")


def log_state_transition(from_state: str, to_state: str, changes: Optional[Dict[str, Any]] = None):
    """Log a state transition.

    Args:
        from_state: Previous state description
        to_state: New state description
        changes: Optional dictionary of what changed
    """
    if not VERBOSE:
        return

    print(f"\n   {Colors.THINKING} {Colors.BOLD}State Transition:{Colors.RESET}")
    print(f"      {Colors.DIM}From: {from_state}{Colors.RESET}")
    print(f"      {Colors.DIM}To: {to_state}{Colors.RESET}")

    if changes:
        print(f"      {Colors.DIM}Changes:{Colors.RESET}")
        for key, value in changes.items():
            print(f"         {Colors.DIM}• {key}: {value}{Colors.RESET}")


def log_metric(name: str, value: Any, unit: str = "", indent: int = 0):
    """Log a performance metric.

    Args:
        name: Metric name
        value: Metric value
        unit: Optional unit (e.g., "s", "KB", "items")
        indent: Indentation level
    """
    prefix = "   " * indent
    value_str = f"{value} {unit}" if unit else str(value)
    print(f"{prefix}{Colors.DIM}├─ {name}: {Colors.RESET}{value_str}")


def log_validation(check: str, passed: bool, details: Optional[str] = None):
    """Log a validation check.

    Args:
        check: What was validated
        passed: Whether validation passed
        details: Optional additional details
    """
    if not VERBOSE:
        return

    status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
    print(f"      {Colors.DIM}Validation: {check} - {status}{Colors.RESET}")

    if details:
        print(f"         {Colors.DIM}{details}{Colors.RESET}")


def log_tree(items: list, indent: int = 0):
    """Log items in a tree structure.

    Args:
        items: List of items to display
        indent: Indentation level
    """
    prefix = "   " * indent

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└─" if is_last else "├─"
        print(f"{prefix}{Colors.DIM}{connector}{Colors.RESET} {item}")


class Timer:
    """Simple timer context manager for measuring execution time."""

    def __init__(self, name: str, verbose_only: bool = True):
        """Initialize timer.

        Args:
            name: Name of the operation being timed
            verbose_only: Only log if verbose mode enabled
        """
        self.name = name
        self.verbose_only = verbose_only
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start the timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and log elapsed time."""
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time

        if not self.verbose_only or VERBOSE:
            if elapsed < 1:
                print(f"      {Colors.CLOCK} {self.name}: {elapsed*1000:.0f}ms")
            else:
                print(f"      {Colors.CLOCK} {self.name}: {elapsed:.1f}s")

    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
