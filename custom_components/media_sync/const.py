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

CONF_CHECK_INTERVAL: Final = "check_interval"

# A scheduled check can only override the direction. Sending no arguments
# leaves the app to use whatever direction its own settings say, so that is
# named honestly rather than being called "both".
CHECK_DIRECTION_APP: Final = "app"
CHECK_DIRECTION_ARGS: Final = {
    CHECK_DIRECTION_APP: (),
    DIRECTION_PULL: (ARG_PULL_ONLY,),
    DIRECTION_PUSH: (ARG_PUSH_ONLY,),
}
CONF_CHECK_DIRECTION: Final = "check_direction"

# 0 turns scheduled checks off, which is the default.
DEFAULT_CHECK_INTERVAL: Final = 0
DEFAULT_CHECK_DIRECTION: Final = DIRECTION_PULL

# --- reviewing what a sync left alone ---------------------------------------
# Decisions are written here for the app's --resolve run to pick up.
DECISIONS_PATH: Final = "media_sync/decisions.tsv"

ARG_RESOLVE: Final = "--resolve"

ACTION_KEEP: Final = "keep"
ACTION_DELETE: Final = "delete"

# The folder a candidate sitting directly at a pair's root is grouped under.
# The app writes this literal, so both halves must agree on it.
ROOT_GROUP: Final = "(root)"

# Which side of a pair still holds a candidate. The app writes these.
SIDE_LOCAL: Final = "local"
SIDE_REMOTE: Final = "remote"

# Form field holding the folders the user chose to keep.
CONF_KEEP: Final = "keep"

# Form field holding the folders the user chose to delete. Kept separate from
# CONF_KEEP so deleting is an outright choice rather than the absence of one.
CONF_DELETE: Final = "delete"

# "Select all" companions for the two review lists. Home Assistant forms are
# not reactive, so these stand in for a full list rather than ticking it.
CONF_KEEP_ALL: Final = "keep_all"
CONF_DELETE_ALL: Final = "delete_all"
