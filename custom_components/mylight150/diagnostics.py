"""MyLight150 diagnostics — collect debug and API informations."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .coordinator import MyLight150Coordinator

_LOGGER = logging.getLogger(__name__)

# Keys to hide in the report — never expose credentials
TO_REDACT = {
    "access_token",
    CONF_PASSWORD,
    CONF_USERNAME,
    "refresh_token",
}

# List of endpoints to call for diagnostics. Each tuple contains a key and the endpoint path.
DIAGNOSTIC_ENDPOINTS: list[tuple[str, str]] = [
    # General information about the API and installation
    ("v2",                              "/v2"),
    ("v2_installation",                 "/v2/installations/{code}"),
    ("v3_contract_energy-pricing",      "/v3/contract/energy-pricing"),
     
    # Live data
    ("v2_home",                         "/v2/installations/{code}/home?msb=msb01"),
    # Options from contracts (MSB, MSP, MSH, etc.)
    ("v3_contract_options",             "/v3/contract/options"),
    ("v3_contract_options_msb",         "/v3/contract/options/msb"),
    ("v3_contract_options_mb",          "/v3/contract/options/mb"),
    ("v3_contract_options_msp",         "/v3/contract/options/msp"),
    ("v3_contract_options_msh",         "/v3/contract/options/msh"),
    ("v3_contract_options_myBatteryWithEms", "/v3/contract/options/myBatteryWithEms"),
    # Savings and money pot
    ("v3_savings",                      "/v3/savings"),
    ("v3_money_pot",                    "/v3/money-pot"),
    # Energy, production and consumption
    ("v3_energies",                     "/v3/energies"),
    ("v3_production",                   "/v3/production"),
    ("v3_production_day",               "/v3/production?aggregation=Days"),
    ("v3_consumption",                  "/v3/consumption"),
    ("v3_consumption_day",              "/v3/consumption?aggregation=Days"),
    # Piloted Equipment (HVAC, water heater, etc.)
    ("v2_equipments",                   "/v2/installations/{code}/equipments"),
    ("v3_equipments",                   "/v3/equipments"),
    ("v3_equipments_hvacAirToWater05",  "/v3/equipments/hvacAirToWater05/heatPump"),
    ("v3_equipments_waterHeater03",     "/v3/equipments/waterHeater03/waterHeater"),
    ("v3_consumption_hvacAirToWater05", "/v3/consumption/hvacAirToWater05?aggregation=Week"),
    ("v3_consumption_waterHeater03",    "/v3/consumption/waterHeater03?aggregation=Week"),
    # MSB (MySmartBattery)
    ("v3_msb_legacy",                   "/v3/msb/legacy"),
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Entry point for diagnostics. Called by HA when user requests a diagnostic report."""
    coordinator: MyLight150Coordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        # Configuration Infos
        "config_entry": async_redact_data(
            {
                "entry_id":   entry.entry_id,
                "version":    entry.version,
                "domain":     entry.domain,
                "title":      entry.title,
                "source":     entry.source,
                "data":       dict(entry.data),
                "options":    dict(entry.options),
            },
            TO_REDACT,
        ),
        # Coordinator status and last data
        "coordinator": {
            "installation_code":    coordinator.installation_code,
            "update_interval_sec":  coordinator.update_interval.total_seconds() if coordinator.update_interval else None,
            "last_update_success":  coordinator.last_update_success,
            "last_exception":       str(coordinator.last_exception) if coordinator.last_exception else None,
        },
        # Last data parsed during the last coordinator update
        "last_data": coordinator.data if coordinator.data else "No data available",
        # Raw dump from the list of endpoints
        "api_dump": await _async_fetch_diagnostic_endpoints(coordinator),
    }


async def _async_fetch_diagnostic_endpoints(
    coordinator: MyLight150Coordinator,
) -> dict[str, Any]:
    """Call each endpoint in DIAGNOSTIC_ENDPOINTS and return the results."""
    code = coordinator.installation_code or "unknown"
    results: dict[str, Any] = {}

    for key, endpoint_template in DIAGNOSTIC_ENDPOINTS:
        # Replace the {code} placeholder with the actual installation code
        endpoint = endpoint_template.replace("{code}", code)
        try:
            _LOGGER.debug("Diagnostics: appel %s", endpoint)
            results[key] = await coordinator._api.async_call_api(endpoint)
        except Exception as err:
            # Catching all exceptions to prevent the diagnostic from being blocked
            results[key] = {"error": str(err)}
            _LOGGER.debug("Diagnostics: Error on requesting %s : %s", endpoint, err)

    return results
