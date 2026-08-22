"""Read and drive the state the Media Sync app records."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Final, Self

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import LOGGER, REQUEST_PATH, STATE_PATH

STATUS_IDLE: Final = "idle"
STATUS_RUNNING: Final = "running"
STATUS_OK: Final = "ok"
STATUS_FAILED: Final = "failed"

STATUSES: Final = [STATUS_IDLE, STATUS_RUNNING, STATUS_OK, STATUS_FAILED]


class MediaSyncError(Exception):
    """Raised when the app's state cannot be read or a run cannot be queued."""


@dataclass(frozen=True, kw_only=True)
class SyncState:
    """Result of the most recent run of the sync script."""

    status: str
    mode: str | None = None
    direction: str | None = None
    started: datetime | None = None
    finished: datetime | None = None
    last_success: datetime | None = None
    pending: list[str]
    error: str | None = None

    @property
    def running(self) -> bool:
        """Return whether a run is currently in progress."""
        return self.status == STATUS_RUNNING

    @classmethod
    def unknown(cls) -> Self:
        """Return the state used before the app has ever run."""
        return cls(status=STATUS_IDLE, pending=[])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Parse the JSON state file written by the sync script."""
        status = data.get("status") or STATUS_IDLE
        return cls(
            status=status if status in STATUSES else STATUS_IDLE,
            mode=data.get("mode") or None,
            direction=data.get("direction") or None,
            started=_parse_timestamp(data.get("started")),
            finished=_parse_timestamp(data.get("finished")),
            last_success=_parse_timestamp(data.get("last_success")),
            pending=[str(item) for item in data.get("pending", [])],
            error=data.get("error") or None,
        )


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse a timestamp written by the sync script."""
    if not isinstance(value, str) or not value:
        return None
    return dt_util.parse_datetime(value)


class MediaSyncClient:
    """Exchange files with the app through the shared config folder."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the client."""
        self._hass = hass
        self._state_file = Path(hass.config.path(STATE_PATH))
        self._request_file = Path(hass.config.path(REQUEST_PATH))

    async def async_get_state(self) -> SyncState:
        """Return the result the app recorded for its last run."""
        return await self._hass.async_add_executor_job(self._read_state)

    def _read_state(self) -> SyncState:
        """Read and parse the state file."""
        try:
            raw = self._state_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return SyncState.unknown()
        except OSError as err:
            raise MediaSyncError(str(err)) from err

        try:
            data = json.loads(raw)
        except ValueError:
            LOGGER.debug("Ignoring malformed state file contents: %s", raw)
            return SyncState.unknown()
        return SyncState.from_dict(data)

    async def async_write_request(self, args: tuple[str, ...]) -> None:
        """Leave the arguments for the next run where the app will find them."""
        await self._hass.async_add_executor_job(self._write_request, args)

    async def async_clear_request(self) -> None:
        """Withdraw a queued request so a later run cannot pick it up."""
        await self._hass.async_add_executor_job(self._clear_request)

    def _clear_request(self) -> None:
        """Remove the request file, ignoring one that is already gone."""
        try:
            self._request_file.unlink(missing_ok=True)
        except OSError as err:
            LOGGER.warning("Could not remove %s: %s", self._request_file, err)

    def _write_request(self, args: tuple[str, ...]) -> None:
        """Write the request file."""
        try:
            self._request_file.parent.mkdir(parents=True, exist_ok=True)
            self._request_file.write_text(
                json.dumps({"args": list(args)}), encoding="utf-8"
            )
        except OSError as err:
            raise MediaSyncError(str(err)) from err
