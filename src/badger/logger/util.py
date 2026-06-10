# Borrowed from bayes_opt
class Colours:
    """Print in nice colours."""

    BLUE = "\033[94m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    END = "\033[0m"
    GREEN = "\033[92m"
    PURPLE = "\033[95m"
    RED = "\033[91m"
    UNDERLINE = "\033[4m"
    YELLOW = "\033[93m"

    @classmethod
    def _wrap_colour(cls, s: str, colour: str) -> str:
        return colour + s + cls.END

    @classmethod
    def black(cls, s: str) -> str:
        """Wrap text in black."""
        return cls._wrap_colour(s, cls.END)

    @classmethod
    def blue(cls, s: str) -> str:
        """Wrap text in blue."""
        return cls._wrap_colour(s, cls.BLUE)

    @classmethod
    def bold(cls, s: str) -> str:
        """Wrap text in bold."""
        return cls._wrap_colour(s, cls.BOLD)

    @classmethod
    def cyan(cls, s: str) -> str:
        """Wrap text in cyan."""
        return cls._wrap_colour(s, cls.CYAN)

    @classmethod
    def darkcyan(cls, s: str) -> str:
        """Wrap text in darkcyan."""
        return cls._wrap_colour(s, cls.DARKCYAN)

    @classmethod
    def green(cls, s: str) -> str:
        """Wrap text in green."""
        return cls._wrap_colour(s, cls.GREEN)

    @classmethod
    def purple(cls, s: str) -> str:
        """Wrap text in purple."""
        return cls._wrap_colour(s, cls.PURPLE)

    @classmethod
    def red(cls, s: str) -> str:
        """Wrap text in red."""
        return cls._wrap_colour(s, cls.RED)

    @classmethod
    def underline(cls, s: str) -> str:
        """Wrap text in underline."""
        return cls._wrap_colour(s, cls.UNDERLINE)

    @classmethod
    def yellow(cls, s: str) -> str:
        """Wrap text in yellow."""
        return cls._wrap_colour(s, cls.YELLOW)
