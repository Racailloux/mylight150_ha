from __future__ import annotations

from logging import Logger, getLogger

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform

LOGGER: Logger = getLogger(__package__)

DOMAIN = "mylight150"
DEFAULT_NAME = "MyLight150"

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
CONF_UPDATE_INITIAL = "update_initial"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_PRICING_BASE = "pricing_base"
CONF_PRICING_OFFPEAK = "pricing_offpeak"
CONF_PRICING_TYPE = "pricing_type"
CONF_PRICING_MODE = "pricing_mode"
CONF_PRICING_TYPE_HPHC = "hphc"
CONF_PRICING_CURRENT = "current_pricing"
CONF_ENERGY_PROD_FROM_SOLAR = "energy_prod_from_solar"
CONF_ENERGY_PROD_TO_MSB = "energy_prod_to_msb"
CONF_ENERGY_PROD_TO_GRID = "energy_prod_to_grid"
CONF_ENERGY_CONSUMPTION = "energy_consumption"
CONF_ENERGY_CONSO_FROM_SOLAR = "energy_conso_from_solar"
CONF_ENERGY_CONSO_FROM_MSB = "energy_conso_from_msb"
CONF_ENERGY_CONSO_FROM_GRID = "energy_conso_from_grid"

REFRESH_DATA_FAILED_EVENT = "refresh_failed"
REFRESH_DATA_COMPLETED_EVENT = "refresh_completed"

MIN_UPDATE_INTERVAL: int = 10
MAX_UPDATE_INTERVAL: int = 30
DEFAULT_UPDATE_INTERVAL: int = 10
DEFAULT_UPDATE_INITIAL: bool = True
DEFAULT_PRICING_BASE: float = 0.23
DEFAULT_PRICING_OFFPEAK: float = 0.14
DEFAULT_PRICING_TYPE: str = "base"


# Platform list to be loaded (other sensors (binary,etc) can be added later.
PLATFORMS: list[Platform] = [
#    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


__all__ = [
    "CONF_DEVICE_ID",
    "CONF_ENERGY_CONSO_FROM_GRID",
    "CONF_ENERGY_CONSO_FROM_MSB",
    "CONF_ENERGY_CONSO_FROM_SOLAR",
    "CONF_ENERGY_CONSUMPTION",
    "CONF_ENERGY_PROD_FROM_SOLAR",
    "CONF_ENERGY_PROD_TO_GRID",
    "CONF_ENERGY_PROD_TO_MSB",
    "CONF_PASSWORD",
    "CONF_PRICING_BASE",
    "CONF_PRICING_CURRENT",
    "CONF_PRICING_OFFPEAK",
    "CONF_PRICING_TYPE",
    "CONF_UPDATE_INTERVAL",
    "CONF_UPDATE_INITIAL",
    "CONF_USERNAME",
    "DEFAULT_PRICING_BASE",
    "DEFAULT_PRICING_OFFPEAK",
    "DEFAULT_PRICING_TYPE",
    "DEFAULT_UPDATE_INTERVAL",
    "DOMAIN",
    "MAX_UPDATE_INTERVAL",
    "MIN_UPDATE_INTERVAL",
    "PLATFORMS",
    "REFRESH_DATA_COMPLETED_EVENT",
    "REFRESH_DATA_FAILED_EVENT",
]
