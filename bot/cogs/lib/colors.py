from bot.cogs.lib import loglevel


class Colors:
    HEADER = '\u001b[95m'
    OKBLUE = '\u001b[94m'
    OKCYAN = '\u001b[96m'
    OKGREEN = '\u001b[92m'
    WARNING = '\u001b[93m'
    FAIL = '\u001b[91m'

    FGBLACK = "\u001b[30m"
    FGRED = "\u001b[31m"
    FGGREEN = "\u001b[32m"
    FGYELLOW = "\u001b[33m"
    FGBLUE = "\u001b[34m"
    FGMAGENTA = "\u001b[35m"
    FGCYAN = "\u001b[36m"
    FGWHITE = "\u001b[37m"

    BGBLACK = "\u001b[40m"
    BGRED = "\u001b[41m"
    BGGREEN = "\u001b[42m"
    BGYELLOW = "\u001b[43m"
    BGBLUE = "\u001b[44m"
    BGMAGENTA = "\u001b[45m"
    BGCYAN = "\u001b[46m"
    BGWHITE = "\u001b[47m"

    RESET = "\u001b[0m"
    BOLD = "\u001b[1m"
    UNDERLINE = "\u001b[4m"
    REVERSE = "\u001b[7m"

    CLEAR = "\u001b[2J"
    CLEARLINE = "\u001b[2K"

    UP = "\u001b[1A"
    DOWN = "\u001b[1B"
    RIGHT = "\u001b[1C"
    LEFT = "\u001b[1D"
    TOP = "\u001b[0;0H"

    NEXTLINE = "\u001b[1E"
    PREVLINE = "\u001b[1F"

    @staticmethod
    def colorize(color, text, bold=False, underline=False):
        if bold:
            text = f"{Colors.BOLD}{text}{Colors.RESET}"
        if underline:
            text = f"{Colors.UNDERLINE}{text}{Colors.RESET}"
        return f"{color}{text}{Colors.RESET}"

    @staticmethod
    def get_color(level: loglevel.LogLevel):
        if level == loglevel.LogLevel.PRINT:
            return Colors.OKCYAN
        elif level == loglevel.LogLevel.DEBUG:
            return Colors.OKBLUE
        elif level == loglevel.LogLevel.INFO:
            return Colors.OKGREEN
        elif level == loglevel.LogLevel.WARNING:
            return Colors.WARNING
        elif level == loglevel.LogLevel.ERROR:
            return Colors.FAIL
        elif level == loglevel.LogLevel.FATAL:
            return Colors.FAIL
        else:
            return Colors.RESET
