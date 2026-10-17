"""Single import point for the schema library (voluptuous / probatio)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import probatio as vol
else:
    import voluptuous as vol

__all__ = ["vol"]
