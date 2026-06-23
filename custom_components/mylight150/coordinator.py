"""MyLight150 DataUpdateCoordinator."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .api import MyLight150ApiClient, MyLight150ApiError, MyLight150AuthError
from .const import (
    DOMAIN,
    CONF_ENERGY_PROD_FROM_SOLAR,
    CONF_ENERGY_PROD_TO_MSB,
    CONF_ENERGY_PROD_TO_GRID,
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_CONSO_FROM_SOLAR,
    CONF_ENERGY_CONSO_FROM_MSB,
    CONF_ENERGY_CONSO_FROM_GRID,
)

STORAGE_KEY = "mylight150_past_energies"
STORAGE_VERSION = 1

_LOGGER = logging.getLogger(__name__)


class MyLight150Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator MyLight150 — coordinate cyclic API calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: MyLight150ApiClient,
        update_interval_minutes: int,
    ) -> None:
        self._api = api
        self.installation_code: str | None = None
        self._last_refresh_date: date | None = None
        # Init storage for long term persistency
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._persistent: dict[str, Any] = {}

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
                self.installation_code = await self._async_update_installation_code()
                _LOGGER.debug("MyLight150: Installation code: %s", self.installation_code)

            data: dict[str, Any] = {}

            # Fetch realtime home data and parse it for sensors
            parsed_data = await self._async_update_home_data()
            if parsed_data:
                data.update(parsed_data)

            # Fetch device data and parse it for sensors
            parsed_data = await self._async_update_devices_data()
            if parsed_data:
                data.update(parsed_data)

            # Fetch energy data and parse it for sensors
            parsed_data = await self._async_update_energy_data()
            if parsed_data:
                data.update(parsed_data)

            # Fetch other data if needed in the future..

            return data

        except MyLight150AuthError as err:
            raise UpdateFailed(f"Authentification error: {err}") from err
        except MyLight150ApiError as err:
            raise UpdateFailed(f"API error: {err}") from err


    # Persistency

    async def async_load_persistent_data(self) -> None:
        """Load persistent data from .storage/ at startup."""
        stored = await self._store.async_load()
        if stored:
            self._persistent.update(stored)
            _LOGGER.debug("MyLight150: Persistent data loaded: %s", self._persistent)
        else:
            self._persistent = {}
            _LOGGER.debug("MyLight150: No persistent data found, starting fresh.")


    async def _async_save_persistent_data(self) -> None:
        """Save persistent data to .storage/ at every first morning update."""
        await self._store.async_save(self._persistent)
        _LOGGER.debug("MyLight150: Persistent data saved: %s", self._persistent)


    # API Calls to MyLight150 endpoints

    async def _async_update_installation_code(self) -> str:
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
            _LOGGER.warning("MyLight150: Error while retrieving /v2 : %s", err)

        raise UpdateFailed("MyLight150: Installation code not found in /v2")
    

    async def _async_update_home_data(self) -> dict[str, Any]:
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
            if parsed.get("msb_state", "idle") == "charging":
                parsed["msb_power"] = parsed.get("msb_power", 0.0) * -1

            _LOGGER.debug("MyLight150: Data parsed for live home: %s", parsed)
            return parsed
        
        except Exception as err:
            _LOGGER.warning("MyLight150: Error while retrieving %s : %s", endpoint, err)
            return {}


    async def _async_update_devices_data(self) -> dict[str, Any]:
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
            _LOGGER.warning("MyLight150: Error while retrieving /v3/equipments : %s", err)
            return {}


    async def _async_update_energy_data(self) -> dict[str, Any]:
        """Fetch all energy data from /v3/consumption and /v3/production endpoints."""
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        strf_today = today.strftime('%Y-%m-%d')
        strf_yesterday = yesterday.strftime('%Y-%m-%d')

        is_first_refresh_of_day = (
            self._last_refresh_date is not None
            and self._last_refresh_date < today
        )

        if self._persistent is None or self._persistent == {}:
            _LOGGER.debug("MyLight150: No persistent data found, start loading historical data...")
            self._persistent: dict[str, Any] = {}

        
        if is_first_refresh_of_day:
            _LOGGER.debug(
                "MyLight150: 1st refresh of day %s — fetching yesterday's final value (%s)",
                strf_today, strf_yesterday,
            )

            # Get yesterday energies and update persistent data
            yesterday_data: dict[str, Any] = {}
            data = await self._async_get_energy_production_days(strf_yesterday)
            if data:
                yesterday_data.update(data)
            data = await self._async_get_energy_consumption_days(strf_yesterday)
            if data:
                yesterday_data.update(data)

            # Save in long term persistancy
            self._persistent[CONF_ENERGY_PROD_FROM_SOLAR]  = self._persistent.get(CONF_ENERGY_PROD_FROM_SOLAR, 0.0)  + yesterday_data.get(CONF_ENERGY_PROD_FROM_SOLAR, 0.0)
            self._persistent[CONF_ENERGY_PROD_TO_MSB]      = self._persistent.get(CONF_ENERGY_PROD_TO_MSB, 0.0)      + yesterday_data.get(CONF_ENERGY_PROD_TO_MSB, 0.0)
            self._persistent[CONF_ENERGY_PROD_TO_GRID]     = self._persistent.get(CONF_ENERGY_PROD_TO_GRID, 0.0)     + yesterday_data.get(CONF_ENERGY_PROD_TO_GRID, 0.0)
            self._persistent[CONF_ENERGY_CONSUMPTION]      = self._persistent.get(CONF_ENERGY_CONSUMPTION, 0.0)      + yesterday_data.get(CONF_ENERGY_CONSUMPTION, 0.0)
            self._persistent[CONF_ENERGY_CONSO_FROM_SOLAR] = self._persistent.get(CONF_ENERGY_CONSO_FROM_SOLAR, 0.0) + yesterday_data.get(CONF_ENERGY_CONSO_FROM_SOLAR, 0.0)
            self._persistent[CONF_ENERGY_CONSO_FROM_MSB]   = self._persistent.get(CONF_ENERGY_CONSO_FROM_MSB, 0.0)   + yesterday_data.get(CONF_ENERGY_CONSO_FROM_MSB, 0.0)
            self._persistent[CONF_ENERGY_CONSO_FROM_GRID]  = self._persistent.get(CONF_ENERGY_CONSO_FROM_GRID, 0.0)  + yesterday_data.get(CONF_ENERGY_CONSO_FROM_GRID, 0.0)
            await self._async_save_persistent_data()
        
        _LOGGER.debug("MyLight150: Fetching energy data for date: %s", strf_today)
        daily: dict[str, Any] = {}
        data = await self._async_get_energy_production_days(strf_today)
        if data:
            daily.update(data)
        data = await self._async_get_energy_consumption_days(strf_today)
        if data:
            daily.update(data)

        # Generate sum of past and daily energies
        total = {
            CONF_ENERGY_PROD_FROM_SOLAR:  self._persistent.get(CONF_ENERGY_PROD_FROM_SOLAR, 0.0)  + daily.get(CONF_ENERGY_PROD_FROM_SOLAR, 0.0),
            CONF_ENERGY_PROD_TO_MSB:      self._persistent.get(CONF_ENERGY_PROD_TO_MSB, 0.0)      + daily.get(CONF_ENERGY_PROD_TO_MSB, 0.0),
            CONF_ENERGY_PROD_TO_GRID:     self._persistent.get(CONF_ENERGY_PROD_TO_GRID, 0.0)     + daily.get(CONF_ENERGY_PROD_TO_GRID, 0.0),
            CONF_ENERGY_CONSUMPTION:      self._persistent.get(CONF_ENERGY_CONSUMPTION, 0.0)      + daily.get(CONF_ENERGY_CONSUMPTION, 0.0),
            CONF_ENERGY_CONSO_FROM_SOLAR: self._persistent.get(CONF_ENERGY_CONSO_FROM_SOLAR, 0.0) + daily.get(CONF_ENERGY_CONSO_FROM_SOLAR, 0.0),
            CONF_ENERGY_CONSO_FROM_MSB:   self._persistent.get(CONF_ENERGY_CONSO_FROM_MSB, 0.0)   + daily.get(CONF_ENERGY_CONSO_FROM_MSB, 0.0),
            CONF_ENERGY_CONSO_FROM_GRID:  self._persistent.get(CONF_ENERGY_CONSO_FROM_GRID, 0.0)  + daily.get(CONF_ENERGY_CONSO_FROM_GRID, 0.0),
        }
                
        _LOGGER.debug(f"MyLight150 total energy data retrieved: {total}")
        self._last_refresh_date = today

        return total


    async def _async_get_energy_production_days(self, start_date: str, days_nr: int = 1) -> dict:
        """Fetch production data from the requested date and number of days."""
        endpoint = f"/v3/production?aggregation=Days&count={days_nr}&date={start_date}"

        def _dest(breakdown: dict, type_name: str) -> float:
            """Extract energy value from production destination list."""
            for item in breakdown.get("destination", []):
                if item.get("type") == type_name:
                    return item.get("measure", {}).get("energy", 0.0)
            return 0.0
        
        try:
            _LOGGER.debug(f"MyLight150: endpoints: {endpoint}")
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_PROD_FROM_SOLAR: breakdown.get("total", 0.0),
                CONF_ENERGY_PROD_TO_MSB:     _dest(breakdown, "virtualBattery"),
                CONF_ENERGY_PROD_TO_GRID:    _dest(breakdown, "injection"),
            }
                    
        except Exception as err:
            _LOGGER.warning("MyLight150: Error while retrieving energy production data : %s from endpoint:%s", err, endpoint)
            return {}


    async def _async_get_energy_consumption_days(self, start_date: str, days_nr: int = 1) -> dict:
        """Fetch consumption data from the requested date and number of days."""
        endpoint = f"/v3/consumption?aggregation=Days&count={days_nr}&date={start_date}"
        
        def _src(breakdown: dict, type_name: str) -> float:
            """Extract energy value from consumption sources list."""
            for item in breakdown.get("sources", {}).get("energies", []):
                if item.get("type") == type_name:
                    return item.get("measure", {}).get("energy", 0.0)
            return 0.0
        
        try:
            _LOGGER.debug(f"MyLight150: endpoints: {endpoint}")
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_CONSUMPTION:      breakdown.get("total", {}).get("energy", 0.0),
                CONF_ENERGY_CONSO_FROM_SOLAR: _src(breakdown, "selfConsumption"),
                CONF_ENERGY_CONSO_FROM_MSB:   _src(breakdown, "virtualBattery"),
                CONF_ENERGY_CONSO_FROM_GRID:  _src(breakdown, "grid"),
            }
                    
        except Exception as err:
            _LOGGER.warning("MyLight150: Error while retrieving energy consumption data : %s from endpoint:%s", err, endpoint)
            return {}


    async def _async_get_energy_production_month(self, year: int, month: int) -> dict:
        """Fetch production data from the requested month."""
        endpoint = f"/v3/production?aggregation=Month&date={year}-{month}-01"
        
        def _dest(breakdown: dict, type_name: str) -> float:
            """Extract energy value from production destination list."""
            for item in breakdown.get("destination", []):
                if item.get("type") == type_name:
                    return item.get("measure", {}).get("energy", 0.0)
            return 0.0
        
        try:
            _LOGGER.debug(f"MyLight150: endpoints: {endpoint}")
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_PROD_FROM_SOLAR: breakdown.get("total", 0.0),
                CONF_ENERGY_PROD_TO_MSB:     _dest(breakdown, "virtualBattery"),
                CONF_ENERGY_PROD_TO_GRID:    _dest(breakdown, "injection"),
            }
                    
        except Exception as err:
            _LOGGER.warning("MyLight150: Error while retrieving energy production data : %s from endpoint:%s", err, endpoint)
            return {}


    async def _async_get_energy_consumption_month(self, year: int, month: int) -> dict:
        """Fetch consumption data from the requested month."""
        endpoint = f"/v3/consumption?aggregation=Month&date={year}-{month}-01"

        def _src(breakdown: dict, type_name: str) -> float:
            """Extract energy value from consumption sources list."""
            for item in breakdown.get("sources", {}).get("energies", []):
                if item.get("type") == type_name:
                    return item.get("measure", {}).get("energy", 0.0)
            return 0.0
        
        try:
            _LOGGER.debug(f"MyLight150: endpoints: {endpoint}")
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_CONSUMPTION:      breakdown.get("total", {}).get("energy", 0.0),
                CONF_ENERGY_CONSO_FROM_SOLAR: _src(breakdown, "selfConsumption"),
                CONF_ENERGY_CONSO_FROM_MSB:   _src(breakdown, "virtualBattery"),
                CONF_ENERGY_CONSO_FROM_GRID:  _src(breakdown, "grid"),
            }
                    
        except Exception as err:
            _LOGGER.warning("MyLight150: Error while retrieving energy consumption data : %s from endpoint:%s", err, endpoint)
            return {}


    async def _async_get_energy_production_year(self, year: int) -> dict:
        """Fetch production data from the requested year."""
        endpoint = f"/v3/production?aggregation=Year&count=1&date={year}-01-01"

        def _dest(breakdown: dict, type_name: str) -> float:
            """Extract energy value from production destination list."""
            for item in breakdown.get("destination", []):
                if item.get("type") == type_name:
                    return item.get("measure", {}).get("energy", 0.0)
            return 0.0
        
        try:
            _LOGGER.debug(f"MyLight150: endpoints: {endpoint}")
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_PROD_FROM_SOLAR: breakdown.get("total", 0.0),
                CONF_ENERGY_PROD_TO_MSB:     _dest(breakdown, "virtualBattery"),
                CONF_ENERGY_PROD_TO_GRID:    _dest(breakdown, "injection"),
            }
                    
        except Exception as err:
            _LOGGER.debug("MyLight150: Error while retrieving energy production data : %s from endpoint:%s", err, endpoint)
            return {}


    async def _async_get_energy_consumption_year(self, year: int) -> dict:
        """Fetch consumption data from the requested year."""
        endpoint = f"/v3/consumption?aggregation=Year&count=1&date={year}-01-01"

        def _src(breakdown: dict, type_name: str) -> float:
            """Extract energy value from consumption sources list."""
            for item in breakdown.get("sources", {}).get("energies", []):
                if item.get("type") == type_name:
                    return item.get("measure", {}).get("energy", 0.0)
            return 0.0
        
        try:
            _LOGGER.debug(f"MyLight150: endpoints: {endpoint}")
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_CONSUMPTION:      breakdown.get("total", {}).get("energy", 0.0),
                CONF_ENERGY_CONSO_FROM_SOLAR: _src(breakdown, "selfConsumption"),
                CONF_ENERGY_CONSO_FROM_MSB:   _src(breakdown, "virtualBattery"),
                CONF_ENERGY_CONSO_FROM_GRID:  _src(breakdown, "grid"),
            }
                    
        except Exception as err:
            _LOGGER.debug("MyLight150: Error while retrieving energy consumption data : %s from endpoint:%s", err, endpoint)
            return {}
