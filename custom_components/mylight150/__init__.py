"""Integration MyLight150 for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .api import MyLight150ApiClient
from .const import (
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    IDENTIFIER,
    PLATFORMS,
)
from .coordinator import MyLight150Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # API instanciation
    api = MyLight150ApiClient(
        hass=hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    # Coordinator instantiation (pooling time comes from option in config entry)
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator = MyLight150Coordinator(
        hass=hass,
        entry=entry,
        api=api,
        update_interval_minutes=update_interval,
    )

    # Restore long term data & First refresh
    await coordinator.async_load_persistent_data()
    await coordinator.async_config_entry_first_refresh()

    # Cleanup all historical devices (old identifier) associated with this config entry
    await _async_cleanup_orphan_devices(
        hass, entry, IDENTIFIER
    )

    # Storing coordinator into hass.data to be acccessible from sensor.py
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Platforms loading
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Listeners loading for option reload
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    # Called when the integration is reloaded or deleted. Unloads platforms and cancels scheduled tasks.
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cancel the coordinator's scheduled tasks and remove it
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Called when any option changed (refresh delay time, etc.)
    _LOGGER.debug("Mofidied options, reloading integration.")
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_cleanup_orphan_devices(
    hass: HomeAssistant, entry: ConfigEntry, valid_identifiers: str | None
) -> None:
    """Delete orphaned devices (old identifier) associated with this config entry."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)

    expected = (DOMAIN, valid_identifiers)
                
    for device in devices:
        if device.identifiers == expected:
            continue

        # Never delete a device that still has active entities
        if er.async_entries_for_device(entity_registry, device.id, include_disabled_entities=True):
            _LOGGER.info(f"Device '{device.name}' does not correspond to any expected identifier but still has entities, not deleting.")
            continue

        _LOGGER.debug(f"Removing orphan device {device.id} (identifiers={device.identifiers})")
        device_registry.async_remove_device(device.id)

