"""Shared helpers for mylight150 entities (sensor, binary_sensor, ...)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, IDENTIFIER


def build_modeled_device_info(model: str) -> DeviceInfo:
    """Single source of truth for the device shared by all platforms with the given model designed."""
    device_info = build_device_info()
    device_info["model"] = model
    return device_info


def build_device_info() -> DeviceInfo:
    """Single source of truth for the device shared by all platforms."""
    return DeviceInfo(
        identifiers={(DOMAIN, IDENTIFIER)},
        name="mylight150",
        manufacturer="mylight systems",
        model="",
        configuration_url=None,
    )
