"""
ANSI styling, color definitions, and ASCII art banners for Xylarium.
Authentic DOS / BBS color palette.
"""

# Text Attributes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"
INVERSE = "\033[7m"

# Standard Foreground Colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# High-Intensity Foreground Colors
BRIGHT_BLACK = "\033[90m"   # Dark Gray
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"  # Amber / Gold
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Background Colors
BG_BLACK = "\033[40m"
BG_BLUE = "\033[44m"
BG_DARK = "\033[48;5;234m"


def c_cyan(text: str) -> str:
    return f"{BRIGHT_CYAN}{text}{RESET}"

def c_gold(text: str) -> str:
    return f"{BRIGHT_YELLOW}{text}{RESET}"

def c_green(text: str) -> str:
    return f"{BRIGHT_GREEN}{text}{RESET}"

def c_red(text: str) -> str:
    return f"{BRIGHT_RED}{text}{RESET}"

def c_magenta(text: str) -> str:
    return f"{BRIGHT_MAGENTA}{text}{RESET}"

def c_white(text: str) -> str:
    return f"{BRIGHT_WHITE}{text}{RESET}"

def c_gray(text: str) -> str:
    return f"{BRIGHT_BLACK}{text}{RESET}"

def c_blue(text: str) -> str:
    return f"{BRIGHT_BLUE}{text}{RESET}"

def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


TITLE_BANNER = f"""{BRIGHT_CYAN}
  ██╗  ██╗██╗   ██╗██╗      █████╗ ██████╗ ██╗██╗   ██╗███╗   ███╗
  ╚██╗██╔╝╚██╗ ██╔╝██║     ██╔══██╗██╔══██╗██║██║   ██║████╗ ████║
   ╚███╔╝  ╚████╔╝ ██║     ███████║██████╔╝██║██║   ██║██╔████╔██║
   ██╔██╗   ╚██╔╝  ██║     ██╔══██║██╔══██╗██║██║   ██║██║╚██╔╝██║
  ██╔╝ ██╗   ██║   ███████╗██║  ██║██║  ██║██║╚██████╔╝██║ ╚═╝ ██║
  ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝
{BRIGHT_YELLOW}   --- [ T H E   B A R R E N   R E A L M S   E L I T E ] ---{RESET}
{BRIGHT_BLACK}   Classic BBS Door Game Kernel (TradeWars 2002 x BRE x SRE){RESET}
"""
