<div align="center">

<img src="https://raw.githubusercontent.com/mkerstner/media-sync/main/media_sync/logo.png" alt="Media Sync" width="420">

<h3>Home Assistant integration for Media Sync</h3>
<p>Buttons, status and deletion confirmation for the app that does the syncing.</p>

<a href="https://github.com/mkerstner/media-sync-integration/releases"><img alt="Release" src="https://img.shields.io/github/v/release/mkerstner/media-sync-integration?style=flat-square"></a>
<a href="https://github.com/mkerstner/media-sync"><img alt="App" src="https://img.shields.io/badge/companion-app-03a9f4?style=flat-square"></a>
<a href="https://hacs.xyz"><img alt="HACS" src="https://img.shields.io/badge/HACS-custom-41bdf5?style=flat-square"></a>

</div>

---

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
| `sensor.media_sync_last_duration` | How long the last run took |
| `sensor.media_sync_next_check` | When the next scheduled check is due |

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

### Scheduled checks

A convenience for the common case. Set an interval and a check runs on its
own, doing exactly what pressing **Sync** does. It is worth having because the
remote server cannot announce its own changes — looking on a timer is the only
way to notice them.

Set it under **Settings → Devices & services → Media Sync → Configure**:

| Setting | Meaning |
| --- | --- |
| Run a check every | Minutes between checks. `0` turns it off, which is the default. |
| Which way a check should sync | `pull` for remote changes only, `push` for the reverse, or leave it on the app setting. |

#### What a check actually runs with

A check is an ordinary run. It takes everything from the app's own settings
and overrides only the direction:

| Setting | Comes from |
| --- | --- |
| Folders, includes, excludes | The app |
| Deletion protection | The app — a check never deletes while it is on |
| Test run only | The app — if that is on, checks change nothing |
| Remove leftover folders | The app |
| Sync log detail | The app |
| Direction | This option, unless left on *Whatever the app is set to* |

So a check cannot do anything a manual Sync would not. If deletion protection
is on, a check that finds deletions raises the usual notification and waits.

#### Choosing an interval

Two sensors help:

- `sensor.media_sync_last_duration` — how long the last run took.
- `sensor.media_sync_next_check` — when the next one is due.

**Watch the duration before shortening the interval.** Every check compares
the whole tree over SSH, so on a large library a check can take minutes, and
an aggressive interval means near-continuous load on both ends. Pick an
interval comfortably longer than a typical run.

#### When an automation is the better answer

The interval is deliberately the only knob. For anything else — conditions, a
schedule helper, reacting to another entity, per-run options — write an
automation calling the Media Sync actions and leave the interval at 0:

```yaml
automation:
  - alias: "Overnight media check"
    triggers:
      - trigger: time_pattern
        hours: "/2"
    conditions:
      - condition: time
        after: "23:00:00"
        before: "07:00:00"
      - condition: state
        entity_id: media_player.living_room
        state: "idle"
    actions:
      - action: media_sync.sync
        data:
          config_entry: 01JQ8ZK4M7WXYZ0123456789AB
          direction: pull
```

That also gives you traces, which the built-in interval does not.

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

## One run at a time

Only one sync runs at once — the Supervisor allows a single instance of the
app, and the integration checks with it before starting anything.

While a run is in progress the buttons go unavailable, so there is nothing
to press. The `media_sync.sync` action still answers with an error naming
when the current run started, which is what an automation needs to see.

## Deletions

When a file is on one side but not the other, there is no way to tell whether
it was deleted there or added here. So with deletion protection on — the
default — nothing is removed automatically. Home Assistant raises a repair
notification listing the items and asks you to decide.

Deletion protection is a setting in the app, and turning it off means runs
delete as they go. No repair notification appears then, because there is
nothing left to confirm.

### Reviewing folder by folder

Opening the notification asks what should happen, folder by folder:

```
Copy to the other side:  [ ] Documents pull — Notes/2019  (12 files, on the server only)
Delete for good:         [x] Documents pull — Notes/2020  (38 files, on Home Assistant only)
```

**Copy** puts files back on the side that is missing them — use it when they
were added, not deleted. **Delete** removes them from the side that still has
them — use it when they were deleted on purpose and that should carry across.

Both lists start empty, so nothing happens by default. Anything you leave out
of both stays pending, so you can decide on part of it now and the rest later.

Copying is what actually clears an item that was *added* on one side. Before
this the only outcomes were "delete everything" or "leave it", so anything left
alone came back on every run.

Three things worth knowing:

- **Grouping is presentation only.** Deciding on a folder acts on the recorded
  candidates inside it and nothing else. A folder holding two candidates
  usually holds hundreds of correctly synced files, and those are never
  touched.
- **The grouping adapts.** It stays as specific as it can and only rolls up to
  a shallower level when there would otherwise be too many rows.
- **Deletions are re-checked as they are applied.** Anything that has since
  appeared on the other side is skipped, so a notification can sit unanswered
  without becoming unsafe.

This needs Media Sync app 1.5.0 or newer. With an older app the notification
falls back to the previous all-or-nothing question.

## Configuration

Only the scheduled check interval, under **Configure**. Which server and which
folders are set up in the app's own settings, so the sync script stays usable
on its own.

---

By Matthias Kerstner ([@mkerstner](https://github.com/mkerstner))
