"""Sensors for MyLight150 integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENERGY_CONSO_FROM_GRID,
    CONF_ENERGY_CONSO_FROM_MSB,
    CONF_ENERGY_CONSO_FROM_SOLAR,
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_PROD_FROM_SOLAR,
    CONF_ENERGY_PROD_TO_GRID,
    CONF_ENERGY_PROD_TO_MSB,
    CONF_PRICING_BASE,
    CONF_PRICING_CURRENT,
    CONF_PRICING_MODE,
    CONF_PRICING_OFFPEAK,
    CONF_PRICING_TYPE,
    DEFAULT_PRICING_BASE,
    DEFAULT_PRICING_OFFPEAK,
    DEFAULT_PRICING_TYPE,
    DOMAIN,
)
from .coordinator import MyLight150Coordinator

_LOGGER = logging.getLogger(__name__)


# Sensors descriptions
@dataclass(frozen=True, kw_only=True)
class MyLight150SensorEntityDescription(SensorEntityDescription):
    """SensorEntityDescription extended with coordinator data_key."""

    data_key: str


# List all sensors
SENSORS: tuple[MyLight150SensorEntityDescription, ...] = (
    # Live powers sensors (kW)
    MyLight150SensorEntityDescription(
        key="solar_production",
        data_key="solar_production",
        has_entity_name=True,
        translation_key="solar_production",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    MyLight150SensorEntityDescription(
        key="grid",
        data_key="grid",
        has_entity_name=True,
        translation_key="grid",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    MyLight150SensorEntityDescription(
        key="load",
        data_key="load",
        has_entity_name=True,
        translation_key="load",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
    ),
    # MySmartBattery (virtual battery) sensors
    MyLight150SensorEntityDescription(
        key="msb_state",
        data_key="msb_state",
        has_entity_name=True,
        translation_key="msb_state",
        icon="mdi:battery-sync",
    ),
    MyLight150SensorEntityDescription(
        key="msb_power",
        data_key="msb_power",
        has_entity_name=True,
        translation_key="msb_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    MyLight150SensorEntityDescription(
        key="msb_autonomy",
        data_key="msb_autonomy",
        has_entity_name=True,
        translation_key="msb_autonomy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    MyLight150SensorEntityDescription(
        key="msb_capacity",
        data_key="msb_capacity",
        has_entity_name=True,
        translation_key="msb_capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-battery",
    ),
    MyLight150SensorEntityDescription(
        key="msb_level",
        data_key="msb_level",
        has_entity_name=True,
        translation_key="msb_level",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    # Money sensors
    MyLight150SensorEntityDescription(
        key="money_pot",
        data_key="money_pot",
        has_entity_name=True,
        translation_key="money_pot",
        native_unit_of_measurement="€",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:piggy-bank",
    ),
    # Equipments sensors
    MyLight150SensorEntityDescription(
        key="heatPump_mode",
        data_key="heatPump_mode",
        has_entity_name=True,
        translation_key="heatpump_mode",
        icon="mdi:heating-coil",
    ),
    MyLight150SensorEntityDescription(
        key="waterHeater_mode",
        data_key="waterHeater_mode",
        has_entity_name=True,
        translation_key="waterheater_mode",
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
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MyLight150Coordinator = hass.data[DOMAIN][entry.entry_id]

    # Common sensors
    sensors: list = [
        MyLight150SensorEntity(coordinator, entry, desc) for desc in SENSORS
    ]

    # Pricing special sensors
    sensors.append(MyLight150PricingModeSensorEntity(coordinator, entry))
    sensors.append(MyLight150CurrentPricingSensorEntity(coordinator, entry))

    async_add_entities(sensors)


class MyLight150SensorEntity(CoordinatorEntity[MyLight150Coordinator], SensorEntity):
    """Sensor entites for MyLight150. Auto pooling is handled by the coordinator."""

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
            name="MyLight150",
            manufacturer="MyLight Systems",
            model="MySmartBattery",
            configuration_url="https://client.mylight150.com",
        )

    @property
    def native_value(self) -> Any:
        """Sensor value coming from coordinator.data. Returns None if data is not available (coordinator not yet refreshed, or key missing)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)


class MyLight150PricingModeSensorEntity(
    CoordinatorEntity[MyLight150Coordinator], SensorEntity
):
    def __init__(
        self,
        coordinator: MyLight150Coordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)

        # unique_id format : {domain}_{entry_id}_{sensor_key}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{CONF_PRICING_MODE}"
        self._attr_key = CONF_PRICING_MODE
        self._attr_has_entity_name = True
        self._attr_translation_key = CONF_PRICING_MODE
        self._attr_icon = "mdi:clock-time-eight-outline"

        # Device association named by installation code
        installation_code = coordinator.installation_code or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, installation_code)},
            name=f"MyLight150 ({installation_code})",
            manufacturer="MyLight Systems",
            model="MySmartBattery",
            configuration_url="https://client.mylight150.com",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._cancel_timer = async_track_time_interval(
            self.hass,
            self._async_update_time,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        if hasattr(self, "_cancel_timer"):
            self._cancel_timer()

    async def _async_update_time(self, _now=None) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        """Return the current pricing mode "peak" or "offpeak" depending on current time."""
        if self.coordinator.data is None:
            return None

        schedule = self.coordinator.hphc_schedule
        if not schedule:
            return "base"

        return _compute_hphc_mode(schedule)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose schedule data in attribute for potential automations."""
        if self.coordinator.data is None:
            return {}
        return {
            "schedule": self.coordinator.hphc_schedule,
        }


class MyLight150CurrentPricingSensorEntity(
    CoordinatorEntity[MyLight150Coordinator], SensorEntity
):
    def __init__(
        self,
        coordinator: MyLight150Coordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

        # unique_id format : {domain}_{entry_id}_{sensor_key}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{CONF_PRICING_CURRENT}"
        self._attr_key = CONF_PRICING_CURRENT
        self._attr_has_entity_name = True
        self._attr_translation_key = CONF_PRICING_CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "€/kWh"
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:currency-eur"

        # Device association named by installation code
        installation_code = coordinator.installation_code or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, installation_code)},
            name=f"MyLight150 ({installation_code})",
            manufacturer="MyLight Systems",
            model="MySmartBattery",
            configuration_url="https://client.mylight150.com",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._cancel_timer = async_track_time_interval(
            self.hass,
            self._async_update_time,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        if hasattr(self, "_cancel_timer"):
            self._cancel_timer()

    async def _async_update_time(self, _now=None) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the current pricing in €/kWh"""
        options = self._entry.options
        pricing_type = self._entry.data.get(CONF_PRICING_TYPE, DEFAULT_PRICING_TYPE)
        tarif_base = options.get(CONF_PRICING_BASE, DEFAULT_PRICING_BASE)
        tarif_offpeak = options.get(CONF_PRICING_OFFPEAK, DEFAULT_PRICING_OFFPEAK)

        if pricing_type != "hphc":  # Standard pricing
            return tarif_base

        # Peak/OffPeak mode: Calculate the current pricing
        schedule = self.coordinator.hphc_schedule
        if not schedule:
            return tarif_base

        current_mode = _compute_hphc_mode(schedule)
        return tarif_offpeak if current_mode == "offpeak" else tarif_base

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose pricings configured for potential automations."""
        options = self._entry.options
        return {
            "tarif_base": options.get(CONF_PRICING_BASE, DEFAULT_PRICING_BASE),
            "tarif_offpeak": options.get(CONF_PRICING_OFFPEAK, DEFAULT_PRICING_OFFPEAK),
            "pricing_type": options.get(CONF_PRICING_TYPE, DEFAULT_PRICING_TYPE),
        }


def _compute_hphc_mode(schedule: list[dict]) -> str:
    now = dt_util.now()
    current_minutes = now.hour * 60 + now.minute

    def _parse_hhmm(time_str: str) -> int:
        """Convert time in number of minutes since midnight."""
        parts = time_str.lower().replace("h", ":").split(":")
        return int(parts[0]) * 60 + int(parts[1])

    for period in schedule:
        start = _parse_hhmm(period.get("start", "00h00"))
        end = _parse_hhmm(period.get("end", "00h00"))
        ptype = period.get("type", "peak").lower()

        # Manage midnight limit
        if end == 0:
            end = 24 * 60

        if start < end:
            if start <= current_minutes < end:
                return ptype
        else:
            if current_minutes >= start or current_minutes < end:
                return ptype

    # Fallback
    return "base"
