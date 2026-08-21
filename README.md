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

## Automations

### First, tell the app which folders to sync

Folders are configured once in the app, not per automation. An automation
decides *when* a sync runs and *how* — never *what*. Open
**Settings → Apps → Media Sync → Configuration** and add a pair for each
folder:

```yaml
folders:
  - name: Movies
    remote: Media/Movies
    local: /media/Movies
    exclude: ""
  - name: Photos
    remote: Media/Photos
    local: /media/Photos
    exclude: /Originals/
```

Both pairs are handled by every run, in one pass.

### Then trigger it

```yaml
automation:
  - alias: "Nightly media sync"
    triggers:
      - trigger: time
        at: "03:30:00"
    actions:
      - action: media_sync.sync
        data:
          config_entry: 01JQ8ZK4M7WXYZ0123456789AB
          direction: both
```

`config_entry` is the hard part to type by hand. Don't — go to
**Developer tools → Actions**, pick **Media Sync: Sync**, choose the
configuration from the dropdown, then switch the editor to YAML and copy what
it produced.

### Options you can vary per run

| Field | Values | Effect |
| --- | --- | --- |
| `direction` | `both`, `pull`, `push` | `both` keeps whichever copy is newer. `pull` only brings files down, `push` only sends them up. |
| `dry_run` | `true`, `false` | Report what would happen and change nothing. |

A weekly rehearsal that changes nothing, so you can see what has drifted:

```yaml
automation:
  - alias: "Weekly media sync rehearsal"
    triggers:
      - trigger: time
        at: "09:00:00"
    conditions:
      - condition: time
        weekday: [sun]
    actions:
      - action: media_sync.sync
        data:
          config_entry: 01JQ8ZK4M7WXYZ0123456789AB
          dry_run: true
```

One-way, after something else has written to the library:

```yaml
      - action: media_sync.sync
        data:
          config_entry: 01JQ8ZK4M7WXYZ0123456789AB
          direction: push
```

### Reacting to what a sync finds

Nothing is ever deleted without you confirming it, so a sync can end with items
waiting on a decision. Tell yourself about it rather than waiting to notice the
repair notification:

```yaml
automation:
  - alias: "Tell me about pending deletions"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.media_sync_pending_deletions
        above: 0
    actions:
      - action: media_sync.get_pending_deletions
        data:
          config_entry: 01JQ8ZK4M7WXYZ0123456789AB
        response_variable: pending
      - action: notify.persistent_notification
        data:
          title: "Media Sync: {{ pending.count }} item(s) to decide on"
          message: >-
            {{ pending.deletions | join('\n') }}
```

`media_sync.get_pending_deletions` returns `count` and `deletions`, so the
message lists the actual paths.

To catch failures, trigger on the status sensor instead:

```yaml
      - trigger: state
        entity_id: sensor.media_sync_status
        to: failed
```

### What automations deliberately cannot do

`media_sync.confirm_deletions` exists, but it requires an administrator and is
meant for a person, not a schedule. Automating it would undo the one safeguard
that stops a sync deleting things on its own — if you automate it anyway, know
that you have turned this into a tool that deletes without asking.

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
