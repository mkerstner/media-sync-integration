"""Constants for the Media Sync integration."""

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "media_sync"

LOGGER = logging.getLogger(__package__)

ADDON_NAME: Final = "Media Sync"

# The Supervisor builds an app's full slug from the repository it was installed
# from, so only this suffix is ours and the rest has to be discovered at
# runtime.
ADDON_SLUG_SUFFIX: Final = "media_sync"

CONF_ADDON_SLUG: Final = "addon_slug"

# Shared with the app through the config folder; all relative to it.
STATE_PATH: Final = "media_sync/state.json"
REQUEST_PATH: Final = "media_sync/request.json"
LOG_PATH: Final = "media_sync/media-sync.log"

UPDATE_INTERVAL_IDLE: Final = timedelta(minutes=5)
UPDATE_INTERVAL_RUNNING: Final = timedelta(seconds=15)

ARG_DRY_RUN: Final = "--dry-run"
ARG_SCAN_ONLY: Final = "--scan-only"
ARG_PULL_ONLY: Final = "--pull-only"
ARG_PUSH_ONLY: Final = "--push-only"
ARG_ASSUME_YES: Final = "--yes"

DIRECTION_BOTH: Final = "both"
DIRECTION_PULL: Final = "pull"
DIRECTION_PUSH: Final = "push"

DIRECTION_ARGS: Final = {
    DIRECTION_BOTH: (),
    DIRECTION_PULL: (ARG_PULL_ONLY,),
    DIRECTION_PUSH: (ARG_PUSH_ONLY,),
}

ISSUE_PENDING_DELETIONS: Final = "pending_deletions"

# Longest list of paths rendered into the repair issue description.
MAX_LISTED_DELETIONS: Final = 25
