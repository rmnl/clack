# -*- coding: utf-8 -*-

# botrlib/__init__.py
#
# Author:      Sergey Lashin
# Copyright:   (c) 2012 LongTail Ad Solutions. All rights reserved.
# License:     BSD 3-Clause License
#              See LICENSE file provided with this project for the
#              license terms.

__version_info__ = ('2', '0', '0')
__version__ = '.'.join(__version_info__)

import logging
try:
    from logging import NullHandler
except ImportError:
    # Python < 2.7
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())

# Remove NullHandler
del NullHandler

from client import Client
