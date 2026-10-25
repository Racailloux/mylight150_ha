"""Shared helpers for mylight150 entities (sensor, binary_sensor, ...)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, IDENTIFIER


def build_device_info() -> DeviceInfo:
    """Single source of truth for the device shared by all platforms.
    Every entity (sensor, binary_sensor, ...) must return exactly the same
    DeviceInfo, so Home Assistant attaches them all to one device.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, IDENTIFIER)},
        name="mylight150",
        manufacturer="mylight150 Systems",
        model="",
        configuration_url="https://client.mylight150.com",
    )
