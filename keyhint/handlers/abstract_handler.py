"""Define Abstract (base) handler for Chain of Responsibility Handlers."""

# Default
import abc
import logging
from typing import Any, Optional


class Handler(abc.ABC):
    """Implements the base handler for chaining.

    The Handler interface declares a method for building the chain of handlers.
    It also declares a method for executing a data.
    """

    @abc.abstractmethod
    def set_next(self, handler: "Handler") -> "Handler":
        """Define handler that is exectued next."""

    @abc.abstractmethod
    def handle(self, data) -> Any:
        """Execute handler logic."""


class AbstractHandler(Handler):
    """Implements he default chaining behavior."""

    _next_handler: Optional[Handler] = None

    def __init__(self):
        """Only prepare logger."""
        self._logger = logging.getLogger(self.__class__.__name__)

    def set_next(self, handler: Handler) -> Handler:
        """Define next handler in chain."""
        self._next_handler = handler
        return handler

    @abc.abstractmethod
    def handle(self, data: Any) -> Any:
        """Run next handler, if there, else return."""
        if self._next_handler:
            return self._next_handler.handle(data)
        return None
