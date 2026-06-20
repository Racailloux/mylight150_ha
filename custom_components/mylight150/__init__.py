"""Intégration MyLight150 pour Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MyLight150ApiClient
from .const import CONF_UPDATE_INTERVAL, CONF_UPDATE_INITIAL, CONF_USERNAME, CONF_PASSWORD, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .coordinator import MyLight150Coordinator

_LOGGER = logging.getLogger(__name__)

# Liste des plateformes à charger (on ajoutera binary_sensor, etc. plus tard)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # API instanciation
    session = async_get_clientsession(hass)
    api = MyLight150ApiClient(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        hass=hass,
    )

    # Coordinator instantiation (pooling time comes from option in config entry)
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator = MyLight150Coordinator(
        hass=hass,
        api=api,
        update_interval_minutes=update_interval,
    )

    # Restore long term data & First refresh
    await coordinator.async_load_persistent_data()
    await coordinator.async_config_entry_first_refresh()

    # Storing coordinator into hass.data to be acccessible from sensor.py
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Platforms loading
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Listeners loading for option reload
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    #Called when the integration is reloaded or deleted. Unloads platforms and cancels scheduled tasks.
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cancel the coordinator's scheduled tasks and remove it
        coordinator: MyLight150Coordinator = hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Called when any option changed (refresh delay time, etc.)
    _LOGGER.debug("Mofidied options, reloading integration.")
    await hass.config_entries.async_reload(entry.entry_id)
