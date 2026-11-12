from __future__ import annotations

from logging import Logger, getLogger

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform

LOGGER: Logger = getLogger(__package__)

DOMAIN = "mylight150"
DEFAULT_NAME = "mylight150"
IDENTIFIER = "ML150"

# --- API ---
API_URL = "https://mltcore-prd-apim.azure-api.net/me"
API_SUBSCRIPTION_KEY = "40aadf2a4bed4231a70c5bb45790a5ed"

# --- OAuth/JWT ---
OAUTH_TENANT_NAME = "mylightb2cprd"
OAUTH_TENANT_ID = "94e468fb-4eba-45a2-a895-5c0524b19d56"
OAUTH_CLIENT_ID = "13cb2062-2b0f-4b72-a84c-a5bcb998e714"
OAUTH_SCOPE = f"{OAUTH_CLIENT_ID} openid profile offline_access"
OAUTH_POLICY_NAME = "B2C_1A_MYLIGHTSYSTEMS_signup_signin"
OAUTH_URL = f"https://{OAUTH_TENANT_NAME}.b2clogin.com/{OAUTH_TENANT_NAME}.onmicrosoft.com/{OAUTH_POLICY_NAME}"
OAUTH_REDIRECT_URI = "https://client.mylight150.com/"


CONF_DEVICE_ID = "device_id"
CONF_ENERGY_CONSO_FROM_GRID = "energy_conso_from_grid"
CONF_ENERGY_CONSO_FROM_MSB = "energy_conso_from_msb"
CONF_ENERGY_CONSO_FROM_SOLAR = "energy_conso_from_solar"
CONF_ENERGY_CONSUMPTION = "energy_consumption"
CONF_ENERGY_PROD_FROM_SOLAR = "energy_prod_from_solar"
CONF_ENERGY_PROD_TO_GRID = "energy_prod_to_grid"
CONF_ENERGY_PROD_TO_MSB = "energy_prod_to_msb"
CONF_MB_AUTONOMY = "mb_autonomy"
CONF_MB_ENERGY_CHARGE = "mb_energy_charge"
CONF_MB_ENERGY_CONSO_FROM_GRID = "mb_energy_conso_from_grid"
CONF_MB_ENERGY_DISCHARGE = "mb_energy_discharge"
CONF_MB_LAST_UPDATE = "mb_last_update"
CONF_MONEY_POT = "money_pot"
CONF_MONEY_POT_EVCHARGER = "money_pot_evcharger"
CONF_MONEY_POT_HEATPUMP = "money_pot_heatpump"
CONF_MONEY_POT_WATERHEATER = "money_pot_waterheater"
CONF_OPTION_EVCHARGER = "option_evcharger"
CONF_OPTION_HEATPUMP = "option_heatpump"
CONF_OPTION_MB = "option_mb"
CONF_OPTION_MSB = "option_msb"
CONF_OPTION_MSP = "option_msp"
CONF_OPTION_WATERHEATER = "option_waterheater"
CONF_PRICING_BASE = "pricing_base"
CONF_PRICING_CURRENT = "current_pricing"
CONF_PRICING_OFFPEAK = "pricing_offpeak"
CONF_PRICING_MODE = "pricing_mode"
CONF_PRICING_TYPE = "pricing_type"
CONF_PRICING_TYPE_HPHC = "hphc"
CONF_UPDATE_INITIAL = "update_initial"
CONF_UPDATE_INTERVAL = "update_interval"
EVCHARGER_CHARGING_CONSUMPTION = "evcharger_charging_consumption"
EVCHARGER_CHARGING_COST = "evcharger_charging_cost"
EVCHARGER_CHARGING_MONEYPOT = "evcharger_charging_moneypot"
EVCHARGER_CHARGING_TYPE = "evcharger_charging_type"
EVCHARGER_STATE = "evcharger_state"

REFRESH_DATA_FAILED_EVENT = "refresh_failed"
REFRESH_DATA_COMPLETED_EVENT = "refresh_completed"

MIN_UPDATE_INTERVAL: int = 10
MAX_UPDATE_INTERVAL: int = 30
DEFAULT_UPDATE_INTERVAL: int = 10
DEFAULT_UPDATE_INITIAL: bool = True
DEFAULT_PRICING_BASE: float = 0.2142
DEFAULT_PRICING_OFFPEAK: float = 0.1589
DEFAULT_PRICING_TYPE: str = "hphc"


# Platform list to be loaded (other sensors (binary,etc) can be added later.
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


__all__ = [
    "CONF_ENERGY_CONSO_FROM_GRID",
    "CONF_ENERGY_CONSO_FROM_MSB",
    "CONF_ENERGY_CONSO_FROM_SOLAR",
    "CONF_ENERGY_CONSUMPTION",
    "CONF_ENERGY_PROD_FROM_SOLAR",
    "CONF_ENERGY_PROD_TO_GRID",
    "CONF_ENERGY_PROD_TO_MSB",
    "CONF_MB_AUTONOMY",
    "CONF_MB_ENERGY_CHARGE",
    "CONF_MB_ENERGY_CONSO_FROM_GRID",
    "CONF_MB_ENERGY_DISCHARGE",
    "CONF_MB_LAST_UPDATE",
    "CONF_MONEY_POT",
    "CONF_MONEY_POT_EVCHARGER",
    "CONF_MONEY_POT_HEATPUMP",
    "CONF_MONEY_POT_WATERHEATER",
    "CONF_OPTION_EVCHARGER",
    "CONF_OPTION_HEATPUMP",
    "CONF_OPTION_MB",
    "CONF_OPTION_MSB",
    "CONF_OPTION_MSP",
    "CONF_OPTION_WATERHEATER",
    "CONF_PASSWORD",
    "CONF_PRICING_BASE",
    "CONF_PRICING_CURRENT",
    "CONF_PRICING_MODE",
    "CONF_PRICING_OFFPEAK",
    "CONF_PRICING_TYPE",
    "CONF_USERNAME",
    "DEFAULT_PRICING_BASE",
    "DEFAULT_PRICING_OFFPEAK",
    "DEFAULT_PRICING_TYPE",
    "DOMAIN",
    "EVCHARGER_CHARGING_CONSUMPTION",
    "EVCHARGER_CHARGING_COST",
    "EVCHARGER_CHARGING_MONEYPOT",
    "EVCHARGER_CHARGING_TYPE",
    "EVCHARGER_STATE",
    "MAX_UPDATE_INTERVAL",
    "MIN_UPDATE_INTERVAL",
    "PLATFORMS",
    "REFRESH_DATA_COMPLETED_EVENT",
    "REFRESH_DATA_FAILED_EVENT",
]
