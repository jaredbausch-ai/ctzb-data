# Session inventory — captured 22 Oct 2026

What the originating conversation had available, so a new project chat can be
checked against it rather than assumed equivalent. Ask a fresh session to list
its connectors, skills and connected folders and compare.

## Connectors

| name | org-level | enabled in that chat |
|---|---|---|
| Gmail | connected | yes |

That is the only one installed. **Two separate switches:** org-level
authentication (per account, carries everywhere) and `enabledInChat` (per
conversation). A new chat can show Gmail authenticated but toggled off — that
is the chat's own connector settings, not a broken connection.

## Skills — 13, all account-level and all enabled

`docs`, `google-workspace`, `computer-use`, `chrome-browser`,
`built-in-browser`, `deep-research`, `import-memory`, `morning`,
`skill-creator`, `xlsx`, `pptx`, `pdf`, `docx`

Account-level, so they are not project-scoped.

## Web

`WebSearch` and `WebFetch` were both available and used.

## The user's computer — THIS IS THE ONE THAT DOES NOT CARRY

Device `magikmoneymachine`, Windows, linked to the conversation via the Claude
desktop app.

**Folder grants are per conversation.** This chat began with
`connectedFolders` empty despite the device being linked, and the grants made
during it (`~/Documents`, `~/Documents/ETH-Indicators`) were explicitly
session-scoped. A new chat starts with none.

To avoid re-granting every time: **Add folder** in the Claude desktop app on
that machine, pointed at `Documents\CTZB`. That is an app-level attachment
rather than a per-chat grant.

Also note: `device_bash` did **not** work on this machine — "the isolated Linux
environment on this device failed to start". So there is no shell on the user's
computer and no `git clone` there. Files move with `device_stage_files` and
`device_commit_files` only, and `.github/workflows/*` is a protected path that
remote writes refuse.

`Documents\CTZB` is therefore a **snapshot, not a clone** — no `.git`, so it
does not pull. GitHub is the live copy. Re-copy it when it matters.

## What cannot transfer at all

The conversation. A new chat gets this repo, not the reasoning that built it.
Anything that was only ever said out loud is gone — see the fractal
checkpoints under Open items in `CONTEXT.md`.
