
import logging as _L
from designkit.behavioral.verboser import VerboseSystem as _V

from finance.config import APP_NAME_CODING as _APP_NAME_CODING, IS_DEV as _IS_DEV


__logger__: _L.Logger   = _L.Logger(_APP_NAME_CODING + '.services.reporter')
__verboser__: _V        = _V(logger=__logger__, is_dev=_IS_DEV)

NEWS_FETCHED = 'Fetched {fetched_count} news items for "{ticker}".'


