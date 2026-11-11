"""mylight150 DataUpdateCoordinator."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from requests.exceptions import JSONDecodeError, RequestException

from .const import (
    CONF_ENERGY_CONSO_FROM_GRID,
    CONF_ENERGY_CONSO_FROM_MSB,
    CONF_ENERGY_CONSO_FROM_SOLAR,
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_PROD_FROM_SOLAR,
    CONF_ENERGY_PROD_TO_GRID,
    CONF_ENERGY_PROD_TO_MSB,
    CONF_MB_AUTONOMY,
    CONF_MB_ENERGY_CHARGE,
    CONF_MB_ENERGY_CONSO_FROM_GRID,
    CONF_MB_ENERGY_DISCHARGE,
    CONF_MB_LAST_UPDATE,
    CONF_OPTION_EVCHARGER,
    CONF_OPTION_HVAC,
    CONF_OPTION_MB,
    CONF_OPTION_MSB,
    CONF_OPTION_MSP,
    CONF_OPTION_WATERHEATER,
    CONF_PRICING_TYPE,
    DEFAULT_PRICING_TYPE,
    DOMAIN,
    EVCHARGER_CHARGING_CONSUMPTION,
    EVCHARGER_CHARGING_COST,
    EVCHARGER_CHARGING_MONEYPOT,
    EVCHARGER_CHARGING_TYPE,
    EVCHARGER_STATE,
)
from .utils.api import Mylight150ApiClient, Mylight150ApiError, Mylight150AuthError
from .utils.persistence import PersistentTotals

# Daily MySmartBattery energy counters list
ENERGY_TOTAL_MSB_KEYS: tuple[str, ...] = (
    CONF_ENERGY_PROD_FROM_SOLAR,
    CONF_ENERGY_PROD_TO_MSB,
    CONF_ENERGY_PROD_TO_GRID,
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_CONSO_FROM_SOLAR,
    CONF_ENERGY_CONSO_FROM_MSB,
    CONF_ENERGY_CONSO_FROM_GRID,
)
# Maximum day to try to retrieve after a long outage.
MAX_CATCHUP_DAYS = 14

_LOGGER = logging.getLogger(__name__)


class Mylight150Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator mylight150 — coordinate cyclic API calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: Mylight150ApiClient,
        update_interval_minutes: int,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._api = api
        self.installation_code: str | None = None
        self._last_refresh_date: date | None = None
        # Long term persistency: cumulative counters + closed periods bookkeeping
        self._totals = PersistentTotals(hass)
        self.hphc_schedule: list[dict] = []
        self._has_mb: bool = False  # MyBattery
        self._has_msb: bool = False  # MySmartBattery
        self._has_msc: bool = False  # MySmartCommunity
        self._has_msh: bool = False  # MySmartHeater
        self._has_msp: bool = False  # MySmartPilot
        self._has_evcharger: bool = False  # EV Charger
        self._has_hvac: bool = False  # HVAC
        self._has_waterheater: bool = False  # Water Heater

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )

    # Cyclic refresh every N minutes from configflow
    async def _async_update_data(self) -> dict[str, Any]:
        """Cyclic refresh every N minutes from config."""
        _LOGGER.info("Coordinator starts retrieving data")
        try:
            # Fetch installation code if not already done > Only needed for historical users
            if not self.installation_code:
                self.installation_code = await self._async_update_installation_code()
                _LOGGER.debug("Installation code: %s", self.installation_code)

            # Determines if this is the first refresh of the day to update pricing data and persistency
            is_first_refresh_of_day = (
                self._last_refresh_date is None
                or self._last_refresh_date != dt_util.now().date()
            )

            data: dict[str, Any] = {}

            # Updates to be done only at first refresh of the day
            if is_first_refresh_of_day:
                _LOGGER.info(
                    "First refresh of the day detected. Updating non frequent data."
                )
                # Update pricing type and schedule in persistent data and config entry
                await self._async_update_pricing_data()
                # Update options
                parsed_data = await self._async_update_options_data()
                _LOGGER.debug(f"Options data retrieved: {parsed_data}")
                if parsed_data:
                    data.update(parsed_data)
            else:
                parsed_data = await self._async_update_options_sensors()
                if parsed_data:
                    data.update(parsed_data)

            # MySmartBattery data retrieval
            if self._has_msb:
                # Fetch virtual MySmartBattery data
                parsed_data = await self._async_update_msb_vbattery_data()
                if parsed_data:
                    data.update(parsed_data)
                # Fetch realtime home data
                parsed_data = await self._async_update_msb_measures_data()
                if parsed_data:
                    data.update(parsed_data)
                # Fetch energy data
                parsed_data = await self._async_update_energy_data()
                if parsed_data:
                    data.update(parsed_data)

            # MyBattery data retrieval
            if self._has_mb:
                # Fetch virtual MyBattery data
                parsed_data = await self._async_update_mb_vbattery_data()
                if parsed_data:
                    data.update(parsed_data)
                # Fetch MyBattery consumption data
                parsed_data = await self._async_update_mb_consumption_data()
                if parsed_data:
                    data.update(parsed_data)
                # Fetch MyBattery injection data
                parsed_data = await self._async_update_mb_injection_data()
                if parsed_data:
                    data.update(parsed_data)

            # MySmartPilot data retrieval
            if self._has_msp:
                # Fetch equipment data
                parsed_data = await self._async_update_equipment_data()
                if parsed_data:
                    data.update(parsed_data)
                    # Update money-pot informations only if equipment managed by mylight150
                    parsed_data = await self._async_update_moneypot_data()
                    if parsed_data:
                        data.update(parsed_data)

            # Update date after having updated all dependent data
            self._last_refresh_date = dt_util.now().date()

            return data

        except Mylight150AuthError as err:
            _LOGGER.warning(f"Authentification error: {err}", err)
        except Mylight150ApiError as err:
            _LOGGER.warning(f"API error: {err}", err)
        return {}

    # Load persistent data for long term persistency
    async def async_load_persistent_data(self) -> None:
        """Load persistent data from storage before the first refresh at startup."""
        await self._totals.async_load()
        _LOGGER.debug(
            f"Persistent data loaded: last closed day {self._totals.last_closed_day_msb_energies}, last closed year {self._totals.last_closed_year_mb_energies}"
        )

    # Fetch installation code for API v2 usage and diagnostics
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
                        _LOGGER.debug(f"Installation code '{code}' found.")
                        return code
        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving installation code.")
            _LOGGER.debug(f"Error while retrieving installation code: {err}")

        return ""

    # Update options data in coordinator and send usefull ones to binary sensors
    async def _async_update_options_data(self) -> dict[str, Any]:
        """Fetch options data."""
        _LOGGER.debug("Updating options data...")

        try:
            data = await self._api.async_call_api("/v3/contract/options")

            _LOGGER.debug("Options data retrieved: %s", data)
            # MyBattery
            self._has_mb = data.get("mb", None) != None
            # MySmartBattery
            self._has_msb = data.get("msb", None) != None
            # MySmartCommunity
            self._has_msc = data.get("msc", None) != None
            # MySmartHeater
            self._has_msh = data.get("msh", None) != None
            # MySmartPilot
            self._has_msp = data.get("msp", None) != None
        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving contract options data.")
            _LOGGER.debug(f"Error while retrieving contract options data: {err}")

        # Update equipment data if MySmartPilot is available
        self._has_evcharger = False
        self._has_hvac = False
        self._has_waterheater = False

        if self._has_msp:
            _LOGGER.debug("MySmartPilot is available for this installation.")
            try:
                data = await self._api.async_call_api("/v3/equipments")
                equipments = data.get("equipments", [])

                for equipment in equipments:
                    equipment_type = equipment.get("equipmentType")

                    if equipment_type and equipment_type == "evCharger":
                        self._has_evcharger = True
                    elif equipment_type and equipment_type == "heatPump":
                        self._has_hvac = True
                    elif equipment_type and equipment_type == "waterHeater":
                        self._has_waterheater = True
            except (
                Mylight150AuthError,
                Mylight150ApiError,
                RequestException,
                JSONDecodeError,
            ) as err:
                _LOGGER.warning("Error while retrieving contract options data.")
                _LOGGER.debug(f"Error while retrieving contract options data: {err}")

        _LOGGER.debug(
            f"Current options detected: MB={self._has_mb}, MSB={self._has_msb}, MSP={self._has_msp}, EV Charger={self._has_evcharger}, HVAC={self._has_hvac}, Water Heater={self._has_waterheater}"
        )
        return await self._async_update_options_sensors()

    # Update options sensors to maintain their state in the coordinator data
    async def _async_update_options_sensors(self) -> dict[str, Any]:
        return {
            CONF_OPTION_MB: self._has_mb,
            CONF_OPTION_MSB: self._has_msb,
            CONF_OPTION_MSP: self._has_msp,
            CONF_OPTION_EVCHARGER: self._has_evcharger,
            CONF_OPTION_HVAC: self._has_hvac,
            CONF_OPTION_WATERHEATER: self._has_waterheater,
        }

    # Fetch instant data for MSB live measures
    async def _async_update_msb_measures_data(self) -> dict[str, Any]:
        """Fetch instant powers (kW) data from /v3/measures endpoint."""
        try:
            data = await self._api.async_call_api("/v3/measures")

            parsed: dict[str, Any] = {
                "solar_production": _safe_get(
                    data, "installation", "productionInKw", default=0.0
                ),
                "grid": _safe_get(data, "installation", "gridInKw", default=0.0)
                - _safe_get(data, "installation", "injectionInKw", default=0.0),
                "load": _safe_get(data, "installation", "consumptionInKw", default=0.0),
            }

            _LOGGER.debug("Data parsed for live home: %s", parsed)
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving home data.")
            _LOGGER.debug(f"Error while retrieving home data: {err}")
        return {}

    # Fetch instant data for MSB virtual battery
    async def _async_update_msb_vbattery_data(self) -> dict[str, Any]:
        """Fetch instant data from /v3/virtual-battery/state endpoint."""
        try:
            data = await self._api.async_call_api("/v3/virtual-battery/state")

            parsed: dict[str, Any] = {
                "msb_state": _safe_get(data, "status", "state", default="unknown"),
                "msb_power": _safe_get(data, "status", "socEvolutionInkW", default=0),
                "msb_autonomy": _safe_get(data, "status", "socInkWh", default=0),
                "msb_capacity": _safe_get(data, "status", "capacity", default=0),
                "msb_level": (
                    _safe_get(data, "status", "socInkWh", default=0)
                    / _safe_get(data, "status", "capacity", default=1)
                    * 100.0
                    if _safe_get(data, "status", "capacity")
                    else 0.0
                ),
            }
            if parsed.get("msb_state", "idle") == "charging":
                parsed["msb_power"] = parsed.get("msb_power", 0.0) * -1

            _LOGGER.debug("Data parsed for MySmartBattery virtual battery: %s", parsed)
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning(
                "Error while retrieving MySmartBattery virtual battery data."
            )
            _LOGGER.debug(
                f"Error while retrieving MySmartBattery virtual battery data: {err}"
            )
        return {}

    # Fetch instant data for MB virtual battery
    async def _async_update_mb_vbattery_data(self) -> dict[str, Any]:
        """Fetch instant data from /v3/mb/dso endpoint."""
        try:
            data = await self._api.async_call_api("/v3/mb/dso")

            lastUpdate = _safe_get(data, "lastUpdatedAt", default=None)
            parsed: dict[str, Any] = {
                CONF_MB_LAST_UPDATE: datetime.strptime(lastUpdate, "%Y-%m-%d").date()
                if lastUpdate
                else None,
                CONF_MB_AUTONOMY: _safe_get(data, "stateOfCharge", default=None),
            }
            _LOGGER.debug(f"Data parsed for MyBattery virtual battery: {parsed}")
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving MyBattery virtual battery data.")
            _LOGGER.debug(
                f"Error while retrieving MyBattery virtual battery data: {err}"
            )
        return {}

    # Fetch yearly data for MB consumption
    async def _async_update_mb_consumption_data(self) -> dict[str, Any]:
        """Fetch all energy data from /v3/mb/dso/consumption/history endpoints."""
        current_year = dt_util.now().date().strftime("%Y")

        try:
            data = await self._api.async_call_api(
                f"/v3/mb/dso/consumption/history?year={current_year}"
            )

            parsed: dict[str, Any] = {
                CONF_MB_ENERGY_CONSO_FROM_GRID: _safe_get(data, "total", default=None),
            }
            _LOGGER.debug(f"Data parsed for MyBattery consumption: {parsed}")
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving MyBattery virtual battery data.")
            _LOGGER.debug(
                f"Error while retrieving MyBattery virtual battery data: {err}"
            )
        return {}

    # Fetch yearly data for MB injection
    async def _async_update_mb_injection_data(self) -> dict[str, Any]:
        """Fetch all energy data from /v3/mb/dso/injection/history endpoints."""
        current_year = dt_util.now().date().strftime("%Y")

        try:
            data = await self._api.async_call_api(
                f"/v3/mb/dso/injection/history?year={current_year}"
            )

            parsed: dict[str, Any] = {
                CONF_MB_ENERGY_CHARGE: _safe_get(
                    data, "performances", "charge", default=None
                ),
                CONF_MB_ENERGY_DISCHARGE: _safe_get(
                    data, "performances", "discharge", default=None
                ),
            }
            _LOGGER.debug(f"Data parsed for MyBattery injection: {parsed}")
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving MyBattery virtual battery data.")
            _LOGGER.debug(
                f"Error while retrieving MyBattery virtual battery data: {err}"
            )
        return {}

    # Fetch instant data of all equipments (evCharger, waterHeater, heatPump)
    async def _async_update_equipment_data(self) -> dict[str, Any]:
        """Fetch equipment data from /v3/equipments endpoint."""
        _LOGGER.debug("Fetching equipment data from API endpoint...")
        try:
            data = await self._api.async_call_api("/v3/equipments")
            equipments = data.get("equipments", [])

            # Initialize equipment data for all known types (evCharger, waterHeater, heatPump)
            parsed: dict[str, Any] = {
                EVCHARGER_STATE: "unavailable",
                EVCHARGER_CHARGING_TYPE: "unavailable",
                EVCHARGER_CHARGING_CONSUMPTION: None,
                EVCHARGER_CHARGING_COST: None,
                EVCHARGER_CHARGING_MONEYPOT: None,
                "waterHeater_mode": "unavailable",
                "heatPump_mode": "unavailable",
            }

            for equipment in equipments:
                equipment_type = equipment.get("equipmentType")

                # Vehicle charger specific data
                if equipment_type and equipment_type == "evCharger":
                    _LOGGER.debug("Processing evCharger equipment...")

                    ev_data = _safe_get(equipment, "state", default="unavailable")
                    parsed.update({EVCHARGER_STATE: ev_data})

                    # EV charger is unplugged, no other charging data available
                    if ev_data == "ready":
                        parsed.update({EVCHARGER_CHARGING_TYPE: "unplugged"})
                        parsed.update({EVCHARGER_CHARGING_CONSUMPTION: 0.0})
                        parsed.update({EVCHARGER_CHARGING_COST: 0.0})
                        parsed.update({EVCHARGER_CHARGING_MONEYPOT: 0.0})
                    # EV charger is plugged, retrieve other charging data
                    else:
                        ev_data = _safe_get(
                            equipment,
                            "currentCharge",
                            "type",
                            default=None,
                        )
                        parsed.update({EVCHARGER_CHARGING_TYPE: ev_data})

                        ev_data = _safe_get(
                            equipment,
                            "currentCharge",
                            "consumption",
                            "value",
                            default=None,
                        )
                        parsed.update({EVCHARGER_CHARGING_CONSUMPTION: ev_data})

                        ev_data = _safe_get(
                            equipment,
                            "currentCharge",
                            "cost",
                            default=None,
                        )
                        parsed.update({EVCHARGER_CHARGING_COST: ev_data})

                        ev_data = _safe_get(
                            equipment,
                            "currentCharge",
                            "moneyPot",
                            default=None,
                        )
                        parsed.update({EVCHARGER_CHARGING_MONEYPOT: ev_data})

                # Water heater and heat pump specific data
                if equipment_type and (
                    equipment_type == "waterHeater" or equipment_type == "heatPump"
                ):
                    _LOGGER.debug(f"Processing {equipment_type} equipment...")
                    current_mode = equipment.get("currentMode")
                    if current_mode:
                        parsed.update({f"{equipment_type}_mode": current_mode})

            _LOGGER.debug("Data parsed for equipments: %s", parsed)
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving equipments.")
            _LOGGER.debug(f"Error while retrieving equipments: {err}")
            return {}

    # Update money-pot data
    async def _async_update_moneypot_data(self) -> dict[str, Any]:
        """Fetch instant data from /v3/money-pot endpoint."""
        try:
            data = await self._api.async_call_api("/v3/money-pot")

            parsed: dict[str, Any] = {
                "money_pot": _safe_get(
                    data, "payload", "balance", "value", default=0.0
                ),
            }
            _LOGGER.debug("Data parsed for money-pot: %s", parsed)
            return parsed

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving money-pot data.")
            _LOGGER.debug(f"Error while retrieving money-pot data: {err}")

        return {}

    # Fetch energy data for consumption and production with persistency management
    async def _async_update_energy_data(self) -> dict[str, Any]:
        """Return the energy totals to display."""
        # Close the days that are finished and not yet counted
        await self._async_close_pending_energy_persistent()

        # Retrieve current daily values
        today_values = await self._async_get_energy_day(dt_util.now().date()) or {}

        total: dict[str, Any] = {}
        for key in ENERGY_TOTAL_MSB_KEYS:
            new_value = self._totals.get(key) + today_values.get(key, 0.0)
            # The API sometimes lowers a value: never display a decrease
            last_known = (self.data or {}).get(key, 0.0) or 0.0
            total[key] = max(new_value, last_known)

        _LOGGER.debug(f"Total energies data retrieved: {total}")
        return total

    async def _async_close_pending_energy_persistent(self) -> None:
        """Add to the counters every finished day that is not counted yet."""
        yesterday = dt_util.now().date() - timedelta(days=1)
        last_closed = self._totals.last_closed_day_msb_energies

        if last_closed is None:
            # First run with this version, start from here
            self._totals.last_closed_day_msb_energies = yesterday
            await self._totals.async_save()
            return

        first = last_closed + timedelta(days=1)
        oldest_allowed = yesterday - timedelta(days=MAX_CATCHUP_DAYS - 1)
        if first < oldest_allowed:
            _LOGGER.warning(
                "Days from %s to %s will not be added (more than %s days missed).",
                first,
                oldest_allowed - timedelta(days=1),
                MAX_CATCHUP_DAYS,
            )
            first = oldest_allowed

        day = first
        while day <= yesterday:
            values = await self._async_get_energy_day(day)
            if values is None:
                # Do not skip the day: nothing is counted, retry at next refresh
                _LOGGER.warning("Energies of %s not available, will retry.", day)
                return
            self._totals.append_values(values, ENERGY_TOTAL_MSB_KEYS)
            self._totals.last_closed_day_msb_energies = day
            await self._totals.async_save()
            _LOGGER.debug("Day %s added to the persistent counters: %s", day, values)
            day += timedelta(days=1)

    async def _async_get_energy_day(self, start: date) -> dict[str, float] | None:
        """Production + consumption for a period, or None if either call failed."""
        values: dict[str, Any] = {}
        data = await self._async_get_energy_production_days(start.isoformat())
        if data:
            values.update(data)
            data = await self._async_get_energy_consumption_days(start.isoformat())
            if data:
                values.update(data)
        if values is None:
            _LOGGER.warning("Energies of %s not available, will retry.", start)
            return None
        return values

    # Fetch energy production data for a given date and number of days
    async def _async_get_energy_production_days(
        self, start_date: str, days_nr: int = 1
    ) -> dict | None:
        """Fetch production data from the requested date and number of days."""
        endpoint = f"/v3/production?aggregation=Days&count={days_nr}&date={start_date}"

        def _dest(breakdown: dict, type_name: str) -> float:
            """Extract energy value from production destination list."""
            for item in breakdown.get("destination", []):
                if item.get("type") == type_name:
                    return _safe_get(item, "measure", "energy", default=0.0)
            return 0.0

        try:
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_PROD_FROM_SOLAR: breakdown.get("total", 0.0),
                CONF_ENERGY_PROD_TO_MSB: _dest(breakdown, "virtualBattery"),
                CONF_ENERGY_PROD_TO_GRID: _dest(breakdown, "injection"),
            }

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving energy production data.")
            _LOGGER.debug(f"Error while retrieving energy production data: {err}")
            return None

    # Fetch energy consumption data for a given date and number of days
    async def _async_get_energy_consumption_days(
        self, start_date: str, days_nr: int = 1
    ) -> dict | None:
        """Fetch consumption data from the requested date and number of days."""
        endpoint = f"/v3/consumption?aggregation=Days&count={days_nr}&date={start_date}"

        def _src(breakdown: dict, type_name: str) -> float:
            """Extract energy value from consumption sources list."""
            for item in _safe_get(breakdown, "sources", "energies", default=[]):
                if item.get("type") == type_name:
                    return _safe_get(item, "measure", "energy", default=0.0)
            return 0.0

        try:
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_CONSUMPTION: _safe_get(
                    breakdown, "total", "energy", default=0.0
                ),
                CONF_ENERGY_CONSO_FROM_SOLAR: _src(breakdown, "selfConsumption"),
                CONF_ENERGY_CONSO_FROM_MSB: _src(breakdown, "virtualBattery"),
                CONF_ENERGY_CONSO_FROM_GRID: _src(breakdown, "grid"),
            }

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving energy consumption data.")
            _LOGGER.debug(f"Error while retrieving energy consumption data: {err}")
            return None

    # Fetch energy production data for a given month of year
    async def _async_get_energy_production_month(
        self, year: int, month: int
    ) -> dict | None:
        """Fetch production data from the requested month."""
        endpoint = f"/v3/production?aggregation=Month&date={year}-{month}-01"

        def _dest(breakdown: dict, type_name: str) -> float:
            """Extract energy value from production destination list."""
            for item in _safe_get(breakdown, "destination", default=[]):
                if item.get("type") == type_name:
                    return _safe_get(item, "measure", "energy", default=0.0)
            return 0.0

        try:
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_PROD_FROM_SOLAR: _safe_get(breakdown, "total", default=0.0),
                CONF_ENERGY_PROD_TO_MSB: _dest(breakdown, "virtualBattery"),
                CONF_ENERGY_PROD_TO_GRID: _dest(breakdown, "injection"),
            }

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving energy production data.")
            _LOGGER.debug(f"Error while retrieving energy production data: {err}")
            return None

    # Fetch energy consumption data for a given month of year
    async def _async_get_energy_consumption_month(
        self, year: int, month: int
    ) -> dict | None:
        """Fetch consumption data from the requested month."""
        endpoint = f"/v3/consumption?aggregation=Month&date={year}-{month}-01"

        def _src(breakdown: dict, type_name: str) -> float:
            """Extract energy value from consumption sources list."""
            for item in _safe_get(breakdown, "sources", "energies", default=[]):
                if item.get("type") == type_name:
                    return _safe_get(item, "measure", "energy", default=0.0)
            return 0.0

        try:
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_CONSUMPTION: _safe_get(
                    breakdown, "total", "energy", default=0.0
                ),
                CONF_ENERGY_CONSO_FROM_SOLAR: _src(breakdown, "selfConsumption"),
                CONF_ENERGY_CONSO_FROM_MSB: _src(breakdown, "virtualBattery"),
                CONF_ENERGY_CONSO_FROM_GRID: _src(breakdown, "grid"),
            }

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving energy consumption data.")
            _LOGGER.debug(f"Error while retrieving energy consumption data: {err}")
            return None

    # Fetch energy production data for a given year
    async def _async_get_energy_production_year(self, year: int) -> dict | None:
        """Fetch production data from the requested year."""
        endpoint = f"/v3/production?aggregation=Year&count=1&date={year}-01-01"

        def _dest(breakdown: dict, type_name: str) -> float:
            """Extract energy value from production destination list."""
            for item in _safe_get(breakdown, "destination", []):
                if item.get("type") == type_name:
                    return _safe_get(item, "measure", "energy", default=0.0)
            return 0.0

        try:
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_PROD_FROM_SOLAR: _safe_get(breakdown, "total", default=0.0),
                CONF_ENERGY_PROD_TO_MSB: _dest(breakdown, "virtualBattery"),
                CONF_ENERGY_PROD_TO_GRID: _dest(breakdown, "injection"),
            }

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving energy production data.")
            _LOGGER.debug(f"Error while retrieving energy production data: {err}")
            return None

    # Fetch energy consumption data for a given year
    async def _async_get_energy_consumption_year(self, year: int) -> dict | None:
        """Fetch consumption data from the requested year."""
        endpoint = f"/v3/consumption?aggregation=Year&count=1&date={year}-01-01"

        def _src(breakdown: dict, type_name: str) -> float:
            """Extract energy value from consumption sources list."""
            for item in _safe_get(breakdown, "sources", "energies", default=[]):
                if item.get("type") == type_name:
                    return _safe_get(item, "measure", "energy", default=0.0)
            return 0.0

        try:
            data = await self._api.async_call_api(endpoint)
            breakdown = data.get("breakdown", {})

            return {
                CONF_ENERGY_CONSUMPTION: _safe_get(
                    breakdown, "total", "energy", default=0.0
                ),
                CONF_ENERGY_CONSO_FROM_SOLAR: _src(breakdown, "selfConsumption"),
                CONF_ENERGY_CONSO_FROM_MSB: _src(breakdown, "virtualBattery"),
                CONF_ENERGY_CONSO_FROM_GRID: _src(breakdown, "grid"),
            }

        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving energy consumption data.")
            _LOGGER.debug(f"Error while retrieving energy consumption data: {err}")
            return None

    # Update pricing type and schedule in persistent data and config entry
    async def _async_update_pricing_data(self) -> bool:
        """Fetch pricing type and schedule to update persistent data."""
        _LOGGER.debug("Updating pricing data...")
        endpoint = "/v3/contract/energy-pricing"
        try:
            pricing_data = await self._api.async_call_api(endpoint)
        except (
            Mylight150AuthError,
            Mylight150ApiError,
            RequestException,
            JSONDecodeError,
        ) as err:
            _LOGGER.warning("Error while retrieving pricing data.")
            _LOGGER.debug(f"Error while retrieving pricing data: {err}")
            return False

        # Update pricing type
        try:
            # Load pricing type from entry and API and update it, if necessary
            pricing_type = pricing_data.get("current", DEFAULT_PRICING_TYPE)
            pricing_type_stored = self._entry.data.get(CONF_PRICING_TYPE, "")

            if pricing_type != pricing_type_stored:
                _LOGGER.info(
                    f"Pricing type change detected! Configuration was '{pricing_type_stored}', new pricing is '{pricing_type}'."
                )
                entry_data = self._entry.data.copy()
                entry_data[CONF_PRICING_TYPE] = pricing_type
                self._hass.config_entries.async_update_entry(
                    self._entry, data=entry_data
                )
                # await self._hass.config_entries.async_reload(self._entry.entry_id)

        except (AttributeError, TypeError, HomeAssistantError) as err:
            _LOGGER.warning("Error while updating pricing type.")
            _LOGGER.debug(f"Error while updating pricing type: {err}")
            return False

        # Update schedule table
        try:
            schedule = pricing_data.get("schedule", {})
            self.hphc_schedule = schedule.get("breakdown", [])
            _LOGGER.debug("peak/offpeak schedule loaded: %s", self.hphc_schedule)
        except (AttributeError, TypeError) as err:
            _LOGGER.warning("Error while retrieving pricing schedule.")
            _LOGGER.debug(f"Error while retrieving pricing schedule: {err}")

        return True


# Retrieve nested values from a dictionary safely
def _safe_get(data: Any, *keys, default=None) -> Any:
    """Navigate nested dicts safely — returns default if any level is None or missing."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current
