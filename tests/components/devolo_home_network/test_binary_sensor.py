"""Tests for the devolo Home Network sensors."""
from unittest.mock import AsyncMock, patch

from devolo_plc_api.exceptions.device import DeviceUnavailable
import pytest

from homeassistant.components.binary_sensor import DOMAIN
from homeassistant.components.devolo_home_network.const import (
    CONNECTED_TO_ROUTER,
    LONG_UPDATE_INTERVAL,
)
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt

from . import configure_integration
from .const import PLCNET_ATTACHED

from tests.common import async_fire_time_changed


@pytest.mark.usefixtures("mock_device", "mock_zeroconf")
async def test_binary_sensor_setup(hass: HomeAssistant):
    """Test default setup of the binary sensor component."""
    entry = configure_integration(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(f"{DOMAIN}.{CONNECTED_TO_ROUTER}") is None

    await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("mock_device", "mock_zeroconf")
async def test_update_attached_to_router(hass: HomeAssistant):
    """Test state change of a attached_to_router binary sensor device."""
    state_key = f"{DOMAIN}.{CONNECTED_TO_ROUTER}"
    entry = configure_integration(hass)

    er = entity_registry.async_get(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Enable entity
    er.async_update_entity(state_key, disabled_by=None)
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt.utcnow() + LONG_UPDATE_INTERVAL)
    await hass.async_block_till_done()

    state = hass.states.get(state_key)
    assert state is not None
    assert state.state == STATE_OFF

    assert er.async_get(state_key).entity_category == EntityCategory.DIAGNOSTIC

    # Emulate device failure
    with patch(
        "devolo_plc_api.plcnet_api.plcnetapi.PlcNetApi.async_get_network_overview",
        side_effect=DeviceUnavailable,
    ):
        async_fire_time_changed(hass, dt.utcnow() + LONG_UPDATE_INTERVAL)
        await hass.async_block_till_done()

        state = hass.states.get(state_key)
        assert state is not None
        assert state.state == STATE_UNAVAILABLE

    # Emulate state change
    with patch(
        "devolo_plc_api.plcnet_api.plcnetapi.PlcNetApi.async_get_network_overview",
        new=AsyncMock(return_value=PLCNET_ATTACHED),
    ):
        async_fire_time_changed(hass, dt.utcnow() + LONG_UPDATE_INTERVAL)
        await hass.async_block_till_done()

        state = hass.states.get(state_key)
        assert state is not None
        assert state.state == STATE_ON

    await hass.config_entries.async_unload(entry.entry_id)
