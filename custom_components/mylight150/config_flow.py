from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig

from .api import MyLight150ApiClient, MyLight150AuthError, MyLight150ApiError
from .const import (
    CONF_PASSWORD,
    CONF_PRICING_TYPE,
    CONF_PRICING_TYPE_HPHC,
    CONF_PRICING_BASE,
    CONF_PRICING_OFFPEAK,
    CONF_UPDATE_INITIAL,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_PRICING_TYPE,
    DEFAULT_PRICING_BASE,
    DEFAULT_PRICING_OFFPEAK,
    DEFAULT_UPDATE_INITIAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


# Numeric selector for pricing inputs
_PRICING_SELECTOR = NumberSelectorConfig(
    min=0.0,
    max=2.0,
    step=0.001,
    unit_of_measurement="€/kWh",
    mode="box",
)


async def _validate_credentials(hass, username: str, password: str) -> tuple[str | None, str]:
    """Try to authenticate. Returns None on success, or an error key string on failure."""
    session = async_get_clientsession(hass)
    api = MyLight150ApiClient(hass, session, username, password)
    try:
    	# Try to connect to MyLight using the given credentials
        await api.async_login_test()
        _LOGGER.info("MyLight150 config flow: connected successfully.")

        # Use the open session to retrieve the pricing type
        pricing_data = await api.async_call_api("/v3/contract/energy-pricing")
        pricing_type = pricing_data.get("current", DEFAULT_PRICING_TYPE)
        _LOGGER.debug("MyLight150 config flow: pricing_type detected = %s", pricing_type)
        
        return None, pricing_type

    except MyLight150AuthError:
        _LOGGER.debug("MyLight150 config flow: invalid_credentials")
        return "invalid_credentials", DEFAULT_PRICING_TYPE
    except MyLight150ApiError:
        _LOGGER.debug("MyLight150 config flow: cannot_connect")
        return "cannot_connect", DEFAULT_PRICING_TYPE
    except Exception:
        _LOGGER.exception("MyLight150 config flow: unexpected error during login")
        return "unexpected", DEFAULT_PRICING_TYPE


class MyLight150ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        # Storage between steps (user > options)
        self._username: str = ""
        self._password: str = ""
        self._pricing_type: str = DEFAULT_PRICING_TYPE

    # Step 1: Credential input & validation
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        _errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            try:
                error_key, pricing_type = await _validate_credentials(
                    self.hass,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                if error_key:
                    _errors["base"] = error_key
                else:
                    # Store validated data for next step
                    self._username = user_input[CONF_USERNAME]
                    self._password = user_input[CONF_PASSWORD]
                    self._pricing_type = pricing_type
                    
                    return await self.async_step_options()

            except Exception:
                _LOGGER.exception("MyLight150: config flow failed")
                _errors["base"] = "unexpected"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=_errors,
        )

    # Step 2: Options (pooling & pricing)
    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        
        if user_input is not None:
            return self.async_create_entry(
                title=self._username,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_PRICING_TYPE: self._pricing_type,
                },
                options={
                    CONF_UPDATE_INTERVAL: int(max(
                        user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                        MIN_UPDATE_INTERVAL,
                    )),
                    CONF_UPDATE_INITIAL: user_input.get(
                        CONF_UPDATE_INITIAL, DEFAULT_UPDATE_INITIAL
                    ),
                    CONF_PRICING_BASE: user_input.get(CONF_PRICING_BASE, DEFAULT_PRICING_BASE),
                    CONF_PRICING_OFFPEAK: user_input.get(CONF_PRICING_OFFPEAK, DEFAULT_PRICING_OFFPEAK),
                },
            )
        # Base schema common for every pricing type
        schema: dict = {
            vol.Required(
                CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
            ): NumberSelector(NumberSelectorConfig(
                min=MIN_UPDATE_INTERVAL,
                max=MAX_UPDATE_INTERVAL,
                mode="slider",
                step=1,
                unit_of_measurement="min",
            )),
            vol.Optional(
                CONF_UPDATE_INITIAL, default=DEFAULT_UPDATE_INITIAL
            ): bool,
            vol.Optional(
                CONF_PRICING_BASE, default=DEFAULT_PRICING_BASE
            ): NumberSelector(_PRICING_SELECTOR),
        }
        # Only for offpeak pricing type
        if self._pricing_type == CONF_PRICING_TYPE_HPHC:
            schema[vol.Optional(
                CONF_PRICING_OFFPEAK, default=DEFAULT_PRICING_OFFPEAK
            )] = NumberSelector(_PRICING_SELECTOR)

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "pricing_type": self._pricing_type,
            },
        )

    # Reconfiguration of the integration: password only
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        _errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            password = user_input[CONF_PASSWORD]

            try:
                error_key, pricing_type = await _validate_credentials(
                    self.hass,
                    reconfigure_entry.data[CONF_USERNAME],
                    password,
                )
                if error_key:
                    _errors["base"] = error_key
                else:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data_updates={CONF_PASSWORD: password, CONF_PRICING_TYPE: pricing_type},
                    )
            except Exception:
                _LOGGER.exception("MyLight150: reconfigure flow failed!")
                _errors["base"] = "unexpected"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_PASSWORD,
                    default=reconfigure_entry.data.get(CONF_PASSWORD, ""),
                ): str,
            }),
            description_placeholders={
                "username": reconfigure_entry.data[CONF_USERNAME],
            },
            errors=_errors,
        )

    @staticmethod
    def async_get_options_flow(configentry: ConfigEntry) -> MyLight150OptionsFlowHandler:
        return MyLight150OptionsFlowHandler()


# Options modifications
class MyLight150OptionsFlowHandler(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # pricing_type stored in the options at 1st config_flow
        pricing_type = self.config_entry.data.get(
            CONF_PRICING_TYPE, DEFAULT_PRICING_TYPE
        )

        if user_input is not None:
            user_input[CONF_UPDATE_INTERVAL] = max(
                int(user_input[CONF_UPDATE_INTERVAL]), MIN_UPDATE_INTERVAL
            )
            return self.async_create_entry(title="", data=user_input)

        # Base Schema
        schema: dict = {
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            ): NumberSelector(NumberSelectorConfig(
                min=MIN_UPDATE_INTERVAL,
                max=MAX_UPDATE_INTERVAL,
                mode="slider",
                step=1,
                unit_of_measurement="min",
            )),
            vol.Optional(
                CONF_UPDATE_INITIAL,
                default=self.config_entry.options.get(
                    CONF_UPDATE_INITIAL, DEFAULT_UPDATE_INITIAL
                ),
            ): bool,
            vol.Optional(
                CONF_PRICING_BASE,
                default=self.config_entry.options.get(CONF_PRICING_BASE, DEFAULT_PRICING_BASE),
            ): NumberSelector(_PRICING_SELECTOR),
        }

        # Tarif offpeak only if type is HPHC
        if pricing_type == CONF_PRICING_TYPE_HPHC:
            schema[vol.Optional(
                CONF_PRICING_OFFPEAK,
                default=self.config_entry.options.get(CONF_PRICING_OFFPEAK, DEFAULT_PRICING_OFFPEAK),
            )] = NumberSelector(_PRICING_SELECTOR)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "pricing_type": pricing_type,
            },
        )


__all__ = ["MyLight150ConfigFlow", "MyLight150OptionsFlowHandler"]
