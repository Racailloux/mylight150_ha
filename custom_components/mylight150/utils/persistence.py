"""mylight150 long-term persistent counters."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_KEY = "mylight150_past_energies"
STORAGE_VERSION = 1

# Bookkeeping entries live in the same storage, under keys starting with "_".
_LAST_DAY = "_last_closed_day_msb_energies"  # "YYYY-MM-DD": last day added to the MySmartBattery energies counters
_LAST_YEAR = "_last_closed_year_mb_energies"  # int: last year added to the MyBattery energies counters


class PersistentTotals:
    """Cumulative counters kept in storage, with the bookkeeping to close periods."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {}

    # Load storage file to fullfil dictionary
    async def async_load(self) -> None:
        """Load the file at startup (empty if it does not exist yet)."""
        stored = await self._store.async_load()
        self._data = dict(stored) if stored else {}

    # Save dictionary data to storage file
    async def async_save(self) -> None:
        """Write the file. Called each time a period is closed."""
        await self._store.async_save(self._data)

    # Send the value of the requested counter/key
    def get(self, key: str) -> float:
        """Accumulated value of a counter (0.0 if unknown)."""
        return float(self._data.get(key, 0.0) or 0.0)

    # Increment the counters listed in keys with the values provided in the dictionary
    def append_values(self, values: dict[str, float], keys: Iterable[str]) -> None:
        """Add the given values to the counters listed in keys."""
        for key in keys:
            self._data[key] = self.get(key) + float(values.get(key, 0.0) or 0.0)

    # Send the date of the last saved data of the daily counters
    @property
    def last_closed_day_msb_energies(self) -> date | None:
        """Last finished day already added to the counters."""
        raw = self._data.get(_LAST_DAY)
        try:
            return date.fromisoformat(raw) if raw else None
        except ValueError:
            return None

    # Save the given date as the last saved data of the daily counters
    @last_closed_day_msb_energies.setter
    def last_closed_day_msb_energies(self, value: date) -> None:
        self._data[_LAST_DAY] = value.isoformat()

    # Send the year nr of the last saved data of the yearly counters
    @property
    def last_closed_year_mb_energies(self) -> int | None:
        """Last finished year already archived."""
        raw = self._data.get(_LAST_YEAR)
        return int(raw) if isinstance(raw, int) else None

    # Save the given year nr as the last saved data of the yearly counters
    @last_closed_year_mb_energies.setter
    def last_closed_year_mb_energies(self, value: int) -> None:
        self._data[_LAST_YEAR] = value
