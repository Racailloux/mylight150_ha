"""Sensors for mylight150 integration."""

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
    EVCHARGER_CHARGING_CONSUMPTION,
    EVCHARGER_CHARGING_COST,
    EVCHARGER_CHARGING_MONEYPOT,
    EVCHARGER_CHARGING_TYPE,
    EVCHARGER_STATE,
    IDENTIFIER,
)
from .coordinator import Mylight150Coordinator

_LOGGER = logging.getLogger(__name__)


# Sensors descriptions
@dataclass(frozen=True, kw_only=True)
class Mylight150SensorEntityDescription(SensorEntityDescription):
    """SensorEntityDescription extended with coordinator data_key."""

    data_key: str


# List all sensors
SENSORS: tuple[Mylight150SensorEntityDescription, ...] = (
    # Live powers sensors (kW)
    Mylight150SensorEntityDescription(
        key="solar_production",
        data_key="solar_production",
        has_entity_name=True,
        translation_key="solar_production",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    Mylight150SensorEntityDescription(
        key="grid",
        data_key="grid",
        has_entity_name=True,
        translation_key="grid",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
        key="msb_state",
        data_key="msb_state",
        has_entity_name=True,
        translation_key="msb_state",
        icon="mdi:battery-sync",
    ),
    Mylight150SensorEntityDescription(
        key="msb_power",
        data_key="msb_power",
        has_entity_name=True,
        translation_key="msb_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
        key="money_pot",
        data_key="money_pot",
        has_entity_name=True,
        translation_key="money_pot",
        native_unit_of_measurement="€",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:piggy-bank",
    ),
    # Equipments sensors
    Mylight150SensorEntityDescription(
        key="heatPump_mode",
        data_key="heatPump_mode",
        has_entity_name=True,
        translation_key="heatpump_mode",
        icon="mdi:heating-coil",
    ),
    Mylight150SensorEntityDescription(
        key="waterHeater_mode",
        data_key="waterHeater_mode",
        has_entity_name=True,
        translation_key="waterheater_mode",
        icon="mdi:water-boiler",
    ),
    Mylight150SensorEntityDescription(
        key=EVCHARGER_STATE,
        data_key=EVCHARGER_STATE,
        has_entity_name=True,
        translation_key=EVCHARGER_STATE,
        icon="mdi:car-electric",
    ),
    Mylight150SensorEntityDescription(
        key=EVCHARGER_CHARGING_TYPE,
        data_key=EVCHARGER_CHARGING_TYPE,
        has_entity_name=True,
        translation_key=EVCHARGER_CHARGING_TYPE,
        icon="mdi:ev-plug-type1",
    ),
    Mylight150SensorEntityDescription(
        key=EVCHARGER_CHARGING_CONSUMPTION,
        data_key=EVCHARGER_CHARGING_CONSUMPTION,
        has_entity_name=True,
        translation_key=EVCHARGER_CHARGING_CONSUMPTION,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:ev-station",
    ),
    Mylight150SensorEntityDescription(
        key=EVCHARGER_CHARGING_COST,
        data_key=EVCHARGER_CHARGING_COST,
        has_entity_name=True,
        translation_key=EVCHARGER_CHARGING_COST,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:cash",
    ),
    Mylight150SensorEntityDescription(
        key=EVCHARGER_CHARGING_MONEYPOT,
        data_key=EVCHARGER_CHARGING_MONEYPOT,
        has_entity_name=True,
        translation_key=EVCHARGER_CHARGING_MONEYPOT,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:piggy-bank",
    ),
    # Total energy sensors (kWh)
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    Mylight150SensorEntityDescription(
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
    coordinator: Mylight150Coordinator = hass.data[DOMAIN][entry.entry_id]

    # Common sensors
    sensors: list = [
        Mylight150SensorEntity(coordinator, entry, desc) for desc in SENSORS
    ]

    # Pricing special sensors
    sensors.append(Mylight150PricingModeSensorEntity(coordinator, entry))
    sensors.append(Mylight150CurrentPricingSensorEntity(coordinator, entry))

    async_add_entities(sensors)


class Mylight150SensorEntity(  # type: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[Mylight150Coordinator], SensorEntity
):
    """Sensor entites for mylight150. Auto pooling is handled by the coordinator."""

    entity_description: Mylight150SensorEntityDescription

    def __init__(
        self,
        coordinator: Mylight150Coordinator,
        entry: ConfigEntry,
        description: Mylight150SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description  # type: ignore[reportIncompatibleVariableOverride]

        # unique_id format : {domain}_{entry_id}_{sensor_key}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"

        # Device association
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, IDENTIFIER)},
            name="mylight150",
            manufacturer="mylight150 Systems",
            model="MySmartBattery",
            configuration_url="https://client.mylight150.com",
        )

    @property
    def native_value(self) -> Any:  # type: ignore[reportIncompatibleVariableOverride]
        """Sensor value coming from coordinator.data. Returns None if data is not available (coordinator not yet refreshed, or key missing)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)


class Mylight150PricingModeSensorEntity(  # type: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[Mylight150Coordinator], SensorEntity
):
    def __init__(
        self,
        coordinator: Mylight150Coordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

        # unique_id format : {domain}_{entry_id}_{sensor_key}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{CONF_PRICING_MODE}"
        self._attr_key = CONF_PRICING_MODE
        self._attr_has_entity_name = True
        self._attr_translation_key = CONF_PRICING_MODE
        self._attr_icon = "mdi:clock-time-eight-outline"

        # Device association
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, IDENTIFIER)},
            name="mylight150",
            manufacturer="mylight150 Systems",
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
    def native_value(self) -> Any:  # type: ignore[reportIncompatibleVariableOverride]
        """Return the current pricing mode "peak" or "offpeak" depending on current time."""
        if self.coordinator.data is None:
            return None

        pricing_type = self._entry.data.get(CONF_PRICING_TYPE, DEFAULT_PRICING_TYPE)
        if pricing_type == "base":  # Base pricing
            return pricing_type

        schedule = self.coordinator.hphc_schedule
        return _compute_hphc_mode(schedule)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[reportIncompatibleVariableOverride]
        """Expose schedule data in attribute for potential automations."""
        if self.coordinator.data is None:
            return {}
        return {
            "schedule": self.coordinator.hphc_schedule,
        }


class Mylight150CurrentPricingSensorEntity(  # type: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[Mylight150Coordinator], SensorEntity
):
    def __init__(
        self,
        coordinator: Mylight150Coordinator,
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
        self._attr_suggested_display_precision = 4
        self._attr_icon = "mdi:currency-eur"

        # Device association
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, IDENTIFIER)},
            name="mylight150",
            manufacturer="mylight150 Systems",
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
    def native_value(self) -> float | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Return the current pricing in €/kWh"""
        options = self._entry.options
        pricing_type = self._entry.data.get(CONF_PRICING_TYPE, DEFAULT_PRICING_TYPE)
        tarif_base = options.get(CONF_PRICING_BASE, DEFAULT_PRICING_BASE)
        tarif_offpeak = options.get(CONF_PRICING_OFFPEAK, DEFAULT_PRICING_OFFPEAK)

        if pricing_type == "base":  # Base pricing
            return tarif_base

        # Peak/OffPeak mode: Calculate the current pricing
        schedule = self.coordinator.hphc_schedule
        if not schedule:
            return tarif_base

        current_mode = _compute_hphc_mode(schedule)
        return tarif_offpeak if current_mode == "offpeak" else tarif_base

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[reportIncompatibleVariableOverride]
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
