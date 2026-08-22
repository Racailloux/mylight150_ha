"""Services for MyLight150 integration"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from requests.exceptions import JSONDecodeError, RequestException

from .api import MyLight150ApiClient, MyLight150ApiError, MyLight150AuthError
from .const import (
    CONF_ENERGY_CONSO_FROM_GRID,
    CONF_ENERGY_CONSO_FROM_MSB,
    CONF_ENERGY_CONSO_FROM_SOLAR,
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_PROD_FROM_SOLAR,
    CONF_ENERGY_PROD_TO_GRID,
    CONF_ENERGY_PROD_TO_MSB,
    DOMAIN,
)
from .coordinator import MyLight150Coordinator, _safe_get

_LOGGER = logging.getLogger(__name__)

SERVICE_IMPORT_STATISTICS = "import_statistics"

ATTR_ENTRY_ID = "entry_id"
API_CALL_DELAY_SECONDS = 0.5

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
    }
)

@callback
async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the two MyLight150 services on the `mylight150` domain."""

    if hass.services.has_service(DOMAIN, SERVICE_IMPORT_STATISTICS):
        return

    # Thin wrappers so the registered handler signature matches what
    # `async_register` expects (a single `ServiceCall` argument), while
    # the actual shared logic (`_async_handle_import`) takes an explicit
    # `external` flag to branch its behaviour.
    async def _async_import_statistics(call: ServiceCall) -> None:
        await _async_handle_import(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_STATISTICS,
        _async_import_statistics,
        schema=SERVICE_SCHEMA,
    )

@callback
async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove both services once no MyLight150 config entry is loaded anymore.
    """
    if hass.data.get(DOMAIN):
        return  # another entry is still loaded, keep the services registered
    hass.services.async_remove(DOMAIN, SERVICE_IMPORT_STATISTICS)

async def _async_handle_import(hass: HomeAssistant, call: ServiceCall) -> None:
    """Service handler for importing statistics from MyLight150 cloud data to recorders."""
    _LOGGER.info("Import historique MyLight150 démarré.")

    entry_id: str = call.data[ATTR_ENTRY_ID]

    # Retrieving and validating the coordinator
    coordinator: MyLight150Coordinator | None = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None:
        _LOGGER.error(
            f"No MyLight150 integration loaded for the given entry_id: '{entry_id}'."
        )
        return
    # Retrieving and validating the API accessor from the coordinator
    api: MyLight150ApiClient | None = coordinator._api
    if api is None:
        _LOGGER.error(
            f"No MyLight150 API access available for the given entry_id: '{entry_id}'."
        )
        return
    
    # Get the contract startup date from the API, to know how far back we can import data.
    try:
        data = await api.async_call_api("/v3/contract")
        contract_date = _safe_get(data, "signedAt", default=date.today())
        _LOGGER.debug(f"Contract started on {contract_date}")

        start_date = dt_util.parse_date(contract_date)
        if start_date is None:
            _LOGGER.error(
                f"Could not parse contract start date '{contract_date}' for entry_id '{entry_id}'."
            )
            return
        end_date = (dt_util.now() - timedelta(days=1)).date()

        if(start_date > end_date):
            _LOGGER.warning(
                f"Contract start date '{start_date}' is after yesterday '{end_date}' for entry_id '{entry_id}'. No data to import."
            )
            return

        _LOGGER.debug(f"Import possible from {start_date.isoformat()} to {end_date.isoformat()}")
        
        # Parse all months between start_date and end_date, and call the import function for each month
        for i in range((end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1):
            delta_month = start_date.month + i

            current_month = start_date.replace(
                year=start_date.year + (delta_month - 1) // 12,
                month=(delta_month - 1) % 12 + 1,
                day=1
            )
            _LOGGER.info(f"Importing data for {current_month.isoformat()}")

            # Intitialize all variables to 0.0 for the current day
            prod_from_solar = 0.0
            prod_to_msb = 0.0
            prod_to_grid = 0.0
            consumption = 0.0
            conso_from_solar = 0.0
            conso_from_msb = 0.0
            conso_from_grid = 0.0

            # Retrieve all production informations
            data = await api.async_call_api(f"/v3/production?aggregation=Days&date={current_month.isoformat()}&count=31")

            production_data = _safe_get(data, "breakdown", "series", default=[])
            if not production_data:
                _LOGGER.warning(f"No production data found for {current_month.isoformat()}")
            else:
                for day_data in production_data:
                    day = _safe_get(day_data, "date")

                    global_data = _safe_get(day_data, "value", "global", default=None)
                    if global_data is not None:
                        for i in global_data:
                            if i.get("type") == "solar":
                                prod_from_solar = _safe_get(i, "measure", "energy", default=0.0)
                                break

                    destination_data = _safe_get(day_data, "value", "destination", default=None)
                    if destination_data is not None:
                        for i in destination_data:
                            if i.get("type") == "virtualBattery":
                                prod_to_msb = _safe_get(i, "measure", "energy", default=0.0)
                            if i.get("type") == "injection":
                                prod_to_grid = _safe_get(i, "measure", "energy", default=0.0)

                    _LOGGER.debug(f"Production on {day}: Solar={prod_from_solar}, VirtualBattery={prod_to_msb}, Injection={prod_to_grid}")

                    # Save data to recorder

            # Retrieve all consumption informations
            data = await api.async_call_api(f"/v3/consumption?aggregation=Days&date={current_month.isoformat()}&count=31")

            consumption_data = _safe_get(data, "breakdown", "series", default=[])
            if not consumption_data:
                _LOGGER.warning(f"No consumption data found for {current_month.isoformat()}")
            else:
                for day_data in consumption_data:
                    day = _safe_get(day_data, "date")

                    consumption = _safe_get(day_data, "value", "total", "energy", default=0.0)

                    sources_data = _safe_get(day_data, "value", "sources", "energies", default=None)
                    if sources_data is not None:
                        for i in sources_data:
                            if i.get("type") == "selfConsumption":
                                conso_from_solar = _safe_get(i, "measure", "energy", default=0.0)
                            if i.get("type") == "virtualBattery":
                                conso_from_msb = _safe_get(i, "measure", "energy", default=0.0)
                            if i.get("type") == "grid":
                                conso_from_grid = _safe_get(i, "measure", "energy", default=0.0)

                    _LOGGER.debug(f"Consumption on {day}: Consumption={consumption}, SelfConsumption={conso_from_solar}, VirtualBatteryConsumption={conso_from_msb}, GridConsumption={conso_from_grid}")

                # Save data to recorder

            # Be a good citizen towards the remote API between two months.
            await asyncio.sleep(API_CALL_DELAY_SECONDS)
        

    except (
        MyLight150AuthError,
        MyLight150ApiError,
        RequestException,
        JSONDecodeError,
    ) as err:
        _LOGGER.warning("Error while retrieving historical data.")
        _LOGGER.debug(f"Error while retrieving historical data: {err}")


"""    
{DOMAIN}_{entry.entry_id}_{description.key}

CONF_ENERGY_PROD_FROM_SOLAR     production: global > solar
CONF_ENERGY_PROD_TO_MSB         production: destination > energies > virtualBattery
CONF_ENERGY_PROD_TO_GRID        production: destination > energies > injection

CONF_ENERGY_CONSUMPTION         consumption: total > energy
CONF_ENERGY_CONSO_FROM_SOLAR    consumption: sources > energies > selfConsumption
CONF_ENERGY_CONSO_FROM_MSB      consumption: sources > energies > virtualBattery
CONF_ENERGY_CONSO_FROM_GRID     consumption: sources > energies > grid
"""