"""WebSocket consumers package for the API app.

This package organizes individual WebSocket consumers into separate
modules, mirroring how REST views are structured under the `views` package.
"""

from .appeals import AppealsConsumer
from .echo import EchoConsumer
from .journal import JournalConsumer

__all__ = ["AppealsConsumer", "EchoConsumer", "JournalConsumer"]


