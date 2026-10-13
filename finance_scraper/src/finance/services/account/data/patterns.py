# ================================================== #
# MODULE: patterns
# ================================================== #


import re

SYMBOL_PATTERN: re.Pattern = re.compile(r'^[A-Z]+[A-Z0-9\.\-]*$')
