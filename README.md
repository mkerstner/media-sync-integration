# Media Sync — Home Assistant integration

Buttons, status and deletion confirmation for the
[Media Sync app](https://github.com/mkerstner/media-sync), which keeps
your media library and a remote server in sync in both directions.

The app does the syncing. This integration gives it a face in Home Assistant.

## Install

Needs [HACS](https://hacs.xyz), and the Media Sync app installed first.

1. In HACS, go to **⋮ → Custom repositories** and add
   `https://github.com/mkerstner/media-sync-integration` with the category **Integration**.
2. Install **Media Sync** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and pick
   **Media Sync**. It only asks you to confirm.

## What you get

| Entity | |
| --- | --- |
| `button.media_sync_sync_now` | Run a full two-way sync |
| `button.media_sync_dry_run` | Show what would happen, change nothing |
| `button.media_sync_scan_for_deletions` | Look for deletions without copying |
| `sensor.media_sync_status` | Idle, running, completed or failed |
| `sensor.media_sync_pending_deletions` | How many items are awaiting a decision |
| `sensor.media_sync_last_successful_sync` | When the last real sync finished |
| `sensor.media_sync_last_run` | When anything last ran |

Actions for automations: `media_sync.sync` (with a direction and a dry-run
option), `media_sync.scan_deletions`, `media_sync.get_pending_deletions`, and
`media_sync.confirm_deletions` for administrators.

## Deletions

When a file is on one side but not the other, there is no way to tell whether
it was deleted there or added here — so nothing is removed automatically.
Home Assistant raises a repair notification listing the items and asks you to
decide.

## Configuration

There is nothing to configure here. Which server and which folders are set up
in the app's own settings, so the sync script stays usable on its own.

---

By Matthias Kerstner ([@mkerstner](https://github.com/mkerstner))
