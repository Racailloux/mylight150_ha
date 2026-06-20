"""Sensors MyLight150."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
from .coordinator import MyLight150Coordinator

_LOGGER = logging.getLogger(__name__)


# ── Descriptions des sensors ─────────────────────────────────────────────────
#
# SensorEntityDescription est un dataclass HA standard.
# On l'étend avec "data_key" pour pointer vers la clé dans coordinator.data.
#
@dataclass(frozen=True, kw_only=True)
class MyLight150SensorEntityDescription(SensorEntityDescription):
    """Description étendue avec la clé dans coordinator.data."""
    data_key: str  #key from dict returned by coordinator._parse_home_data()


# List all sensors
SENSORS: tuple[MyLight150SensorEntityDescription, ...] = (

    # Live powers sensors (kW)
    MyLight150SensorEntityDescription(
        key="solar_production",
        data_key="solar_production",
        has_entity_name = True,
        translation_key= "solar_production",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    MyLight150SensorEntityDescription(
        key="grid",
        data_key="grid",
        has_entity_name = True,
        translation_key= "grid",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    MyLight150SensorEntityDescription(
        key="injection",
        data_key="injection",
        has_entity_name = True,
        translation_key= "injection",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
    ),
    MyLight150SensorEntityDescription(
        key="load",
        data_key="load",
        has_entity_name = True,
        translation_key= "load",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
    ),

    # MySmartBattery (virtual battery) sensors
    MyLight150SensorEntityDescription(
        key="msb_state",
        data_key="msb_state",
        has_entity_name = True,
        translation_key= "msb_state",
        # Text status, no unit, no device class
        icon="mdi:battery-sync",
    ),
    MyLight150SensorEntityDescription(
        key="msb_power",
        data_key="msb_power",
        has_entity_name = True,
        translation_key= "msb_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    MyLight150SensorEntityDescription(
        key="msb_autonomy",
        data_key="msb_autonomy",
        has_entity_name = True,
        translation_key= "msb_autonomy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    MyLight150SensorEntityDescription(
        key="msb_capacity",
        data_key="msb_capacity",
        has_entity_name = True,
        translation_key= "msb_capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-battery",
    ),
    MyLight150SensorEntityDescription(
        key="msb_level",
        data_key="msb_level",
        has_entity_name = True,
        translation_key= "msb_level",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),

    # Savings sensor
    MyLight150SensorEntityDescription(
        key="savings",
        data_key="savings",
        has_entity_name = True,
        translation_key= "savings",
        native_unit_of_measurement="EUR",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:piggy-bank",
    ),

    # Equipments sensors
    MyLight150SensorEntityDescription(
        key="heatPump_mode",
        data_key="heatPump_mode",
        has_entity_name = True,
        translation_key= "heatpump_mode",
        # Text status, no unit, no device class
        icon="mdi:heating-coil",
    ),
    MyLight150SensorEntityDescription(
        key="waterHeater_mode",
        data_key="waterHeater_mode",
        has_entity_name = True,
        translation_key= "waterheater_mode",
        # Text status, no unit, no device class
        icon="mdi:water-boiler",
    ),

    # Total energy sensors (kWh)
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_PROD_FROM_SOLAR,
        data_key=CONF_ENERGY_PROD_FROM_SOLAR,
        has_entity_name=True,
        translation_key=CONF_ENERGY_PROD_FROM_SOLAR,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power",
    ),
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_PROD_TO_MSB,
        data_key=CONF_ENERGY_PROD_TO_MSB,
        has_entity_name=True,
        translation_key=CONF_ENERGY_PROD_TO_MSB,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-up",
    ),
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_PROD_TO_GRID,
        data_key=CONF_ENERGY_PROD_TO_GRID,
        has_entity_name=True,
        translation_key=CONF_ENERGY_PROD_TO_GRID,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
    ),
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_CONSUMPTION,
        data_key=CONF_ENERGY_CONSUMPTION,
        has_entity_name=True,
        translation_key=CONF_ENERGY_CONSUMPTION,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt",
    ),
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_CONSO_FROM_SOLAR,
        data_key=CONF_ENERGY_CONSO_FROM_SOLAR,
        has_entity_name=True,
        translation_key=CONF_ENERGY_CONSO_FROM_SOLAR,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power-variant",
    ),
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_CONSO_FROM_MSB,
        data_key=CONF_ENERGY_CONSO_FROM_MSB,
        has_entity_name=True,
        translation_key=CONF_ENERGY_CONSO_FROM_MSB,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-down",
    ),
    MyLight150SensorEntityDescription(
        key=CONF_ENERGY_CONSO_FROM_GRID,
        data_key=CONF_ENERGY_CONSO_FROM_GRID,
        has_entity_name=True,
        translation_key=CONF_ENERGY_CONSO_FROM_GRID,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MyLight150Coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        MyLight150SensorEntity(coordinator, entry, description)
        for description in SENSORS
    )


class MyLight150SensorEntity(CoordinatorEntity[MyLight150Coordinator], SensorEntity):
    """ Sensor entites for MyLight150. Auto pooling is handled by the coordinator."""

    entity_description: MyLight150SensorEntityDescription

    def __init__(
        self,
        coordinator: MyLight150Coordinator,
        entry: ConfigEntry,
        description: MyLight150SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        # unique_id format : {domain}_{entry_id}_{sensor_key}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"

        # Device association named by installation code
        installation_code = coordinator.installation_code or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, installation_code)},
            name=f"MyLight150 ({installation_code})",
            manufacturer="MyLight Systems",
            model="MySmartBattery",
            configuration_url="https://client.mylight150.com",
        )

    @property
    def native_value(self) -> Any:
        """ Sensor value coming from coordinator.data. Returns None if data is not available (coordinator not yet refreshed, or key missing)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)
