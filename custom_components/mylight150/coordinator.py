"""MyLight150 DataUpdateCoordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MyLight150ApiClient, MyLight150ApiError, MyLight150AuthError
from .const import CONF_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyLight150Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator MyLight150 — orchestre les appels API périodiques et nocturnes."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: MyLight150ApiClient,
        update_interval_minutes: int,
    ) -> None:
        self._api = api
        self.installation_code: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )


    async def _async_update_data(self) -> dict[str, Any]:
        """Cyclic refresh every N minutes from config."""
        _LOGGER.info("MyLight150: Start retrieving data")
        try:
            # Fetch installation code if not already done
            if not self.installation_code:
                self.installation_code = await self._fetch_installation_code()
                _LOGGER.debug("MyLight150: Installation code: %s", self.installation_code)

            data: dict[str, Any] = {}

            # Fetch realtime home data and parse it for sensors
            parsed_data = await self._fetch_home_data()
            if parsed_data is not {}:
                data.update(parsed_data)

            # Fetch device data and parse it for sensors
            parsed_data = await self._fetch_device_data()
            if parsed_data is not {}:
                data.update(parsed_data)

            # Fetch other data (historical, savings, etc.) if needed in the future

            return data

        except MyLight150AuthError as err:
            raise UpdateFailed(f"Erreur d'authentification : {err}") from err
        except MyLight150ApiError as err:
            raise UpdateFailed(f"Erreur API : {err}") from err


    async def async_setup_nightly_refresh(self) -> None:
        """Nightly refresh at 00h30 for aggregated data (historical, savings, etc.)"""
        @callback
        def _nightly_refresh_callback(*_: Any) -> None:
            """Callback called at 00h30."""
            self.hass.async_create_task(self._async_nightly_update())

        # storing unsubscribe function to cancel the nightly refresh when unloading the integration
        self._nightly_unsubscribe = async_track_time_change(
            self.hass,
            _nightly_refresh_callback,
            hour=0,
            minute=30,
            second=0,
        )
        _LOGGER.debug("MyLight150: Nightly coordinator refresh planned at 00h30.")


    async def _async_nightly_update(self) -> None:
        """Nightly API calls for aggregated data (historical, savings, etc.)."""
        _LOGGER.debug("MyLight150: Nightly refresh started.")

# TODO: Call /v3/savings, /v3/production, /v3/consumption, etc.
# Data will be merged into self.data via async_set_updated_data()

        _LOGGER.debug("MyLight150: Nightly refresh completed")


    def async_teardown(self) -> None:
        """Cancel nightly refresh when unloading the integration."""
        if hasattr(self, "_nightly_unsubscribe"):
            self._nightly_unsubscribe()
            _LOGGER.debug(f"MyLight150: Nightly refresh canceled.")


    # API Calls to MyLight150 endpoints

    async def _fetch_installation_code(self) -> str:
        """Fetch installation code from /v2 endpoint."""
        try:
            v2_data = await self._api.async_call_api("/v2")
            # Searching for "installation" link
            for link in v2_data.get("links", []):
                if link.get("rel") == "installation":
                    href = link.get("href", "")
                    code = href.rstrip("/").split("/")[-1]
                    if code:
                        _LOGGER.debug(f"MyLight150: Installation code '{code}' found.")
                        return code
        except Exception as err:
            _LOGGER.debug("Diagnostics: Error while retrieving /v2 : %s", err)

        raise UpdateFailed("MyLight150: Installation code not found in /v2")
    

    async def _fetch_home_data(self) -> dict[str, Any]:
        """Fetch instant data from /v2/installations/{code}/home?msb=msb01 endpoint."""
        endpoint = f"/v2/installations/{self.installation_code}/home?msb=msb01"
        try:
            data = await self._api.async_call_api(endpoint)
        
            """Parse device data from /v2/installations/{code}/home?msb=msb01 endpoint."""
            if data.get("msb", {}).get("capacity", {}).get("value"):
                msb_level = 100.0 * (float)(data.get("msb", {}).get("autonomy", {}).get("value")) / (float)(data.get("msb", {}).get("capacity", {}).get("value"))
            else: msb_level = 0.0
            
            parsed: dict[str, Any] = {
                # Live powers (kW)
                "solar_production":  data.get("solarProduction", {}).get("value"),
                "grid":              data.get("grid", {}).get("value"),
                "injection":         data.get("injection", {}).get("value"),
                "load":              data.get("load", {}).get("value"),
                # MySmartBattery (virtual battery)
                "msb_state":         data.get("msb", {}).get("state"),
                "msb_power":         data.get("msb", {}).get("power", {}).get("value"),
                "msb_autonomy":      data.get("msb", {}).get("autonomy", {}).get("value"),
                "msb_capacity":      data.get("msb", {}).get("capacity", {}).get("value"),
                "msb_level":         msb_level,
                # Saving (weekly display)
                "savings":           data.get("savings", {}).get("amount", {}).get("value"),
                # Timestamp of the data (UTC)
                "timestamp":         data.get("timestamp"),
            }

            _LOGGER.debug("MyLight150: Data parsed for live home: %s", parsed)
            return parsed
        
        except Exception as err:
            _LOGGER.debug("Diagnostics: Error while retrieving %s : %s", endpoint, err)
            return {}


    async def _fetch_device_data(self) -> dict[str, Any]:
        """Fetch device data from /v3/equipments endpoint."""
        try:
            data = await self._api.async_call_api("/v3/equipments")
        
            """Parse device data from /v3/equipments endpoint."""
            equipments = data.get("equipments", [])

            parsed: dict[str, Any] = {}
            
            for equipment in equipments:
                equipment_type = equipment.get("equipmentType")
                current_mode = equipment.get("currentMode")
                if equipment_type and current_mode:
                    parsed.update({f"{equipment_type}_mode": current_mode})

            _LOGGER.debug("MyLight150: Data parsed for equipments: %s", parsed)
            return parsed
        
        except Exception as err:
            _LOGGER.debug("Diagnostics: Error while retrieving /v3/equipments : %s", err)
            return {}
