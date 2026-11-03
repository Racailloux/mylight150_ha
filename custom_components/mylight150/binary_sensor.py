"""Binary sensors mylight150 integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_OPTION_EVCHARGER,
    CONF_OPTION_HVAC,
    CONF_OPTION_MB,
    CONF_OPTION_MSB,
    CONF_OPTION_MSP,
    CONF_OPTION_WATERHEATER,
    DOMAIN,
)
from .coordinator import Mylight150Coordinator
from .entity import build_device_info


# List all binary sensors
BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=CONF_OPTION_MB,
        translation_key=CONF_OPTION_MB,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key=CONF_OPTION_MSB,
        translation_key=CONF_OPTION_MSB,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key=CONF_OPTION_MSP,
        translation_key=CONF_OPTION_MSP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key=CONF_OPTION_EVCHARGER,
        translation_key=CONF_OPTION_EVCHARGER,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key=CONF_OPTION_HVAC,
        translation_key=CONF_OPTION_HVAC,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key=CONF_OPTION_WATERHEATER,
        translation_key=CONF_OPTION_WATERHEATER,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Mylight150Coordinator = hass.data[DOMAIN][entry.entry_id]

    # Common sensors
    sensors: list = [
        Mylight150OptionBinarySensor(coordinator, entry, desc)
        for desc in BINARY_SENSORS
    ]

    async_add_entities(sensors)


class Mylight150OptionBinarySensor(  # type: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[Mylight150Coordinator], BinarySensorEntity
):
    """On when the option is active on the MyLight150 account."""

    _attr_has_entity_name = True
    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: Mylight150Coordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description  # type: ignore[reportIncompatibleVariableOverride]

        # unique_id format : {domain}_{entry_id}_{key}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"

        # Same device as the sensors, built by the shared helper
        self._attr_device_info = build_device_info()

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        """True if the option key is in the list pushed by the coordinator."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.key)
        return value if isinstance(value, bool) else None
