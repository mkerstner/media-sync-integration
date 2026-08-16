"""Sensors for the Media Sync integration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .client import STATUSES, SyncState
from .coordinator import MediaSyncConfigEntry
from .entity import MediaSyncEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MediaSyncSensorEntityDescription(SensorEntityDescription):
    """Describes a Media Sync sensor entity."""

    value_fn: Callable[[SyncState], StateType | datetime]


SENSORS: tuple[MediaSyncSensorEntityDescription, ...] = (
    MediaSyncSensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        value_fn=lambda state: state.status,
    ),
    MediaSyncSensorEntityDescription(
        key="pending_deletions",
        translation_key="pending_deletions",
        value_fn=lambda state: len(state.pending),
    ),
    MediaSyncSensorEntityDescription(
        key="last_successful_sync",
        translation_key="last_successful_sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: state.last_success,
    ),
    MediaSyncSensorEntityDescription(
        key="last_run",
        translation_key="last_run",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.finished,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MediaSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Media Sync sensors."""
    async_add_entities(
        MediaSyncSensor(entry.runtime_data, description)
        for description in SENSORS
    )


class MediaSyncSensor(MediaSyncEntity, SensorEntity):
    """Exposes one field of the last recorded sync result."""

    entity_description: MediaSyncSensorEntityDescription

    @property
    @override
    def native_value(self) -> StateType | datetime:
        """Return the value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
