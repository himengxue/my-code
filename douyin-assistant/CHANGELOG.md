# Changes

## Windows validation and DSH compatibility patch candidate — 2026-10-24

- Respect project state for Windows browser profiles; make UID security tests portable while retaining Linux/Windows sandbox flag checks.
- Match the editor's terminal U+200B marker, saved AI declaration sections and current creator cards; cross-check card IDs against the explicit self-post container.
- Bind reply input/send controls to the selected comment card. Detect SMS verification and exclude disabled drafts from reply evidence; retain uncertain state for current-page-only replies and prevent redispatch.
- Add a root discovery wrapper pointing to the canonical skill, a read-only binding resolver and relocation/DSH provider tests.
- Record one actual Windows CLI public video and successful real-comment reading. Comment submission hit SMS verification; the earlier false-positive confirmed result is retained and explicitly corrected in the audit.
- No account data, generated media, credentials, installed dependencies or private machine paths are included.

## 2.0.0 source release candidate — 2026-10-24

- Preserve original MIT notices and pinned douyin-skills attribution.
- Add Linux project-relative launcher and isolated project HOME/state; preserve a Windows launcher (not revalidated).
- Remove automation-hiding and no-sandbox browser launch branches.
- Stop on verification/risk without automatic reconnect or retry.
- Add 12 offline behavior and 3 security regression tests.
- Use relocatable skill bindings and deny-by-default example policy when local policy is absent.
- Exclude accounts, authorization, generated media, logs, installed dependencies and downloaded binaries.
- Document the sandbox browser launch blocker and untested end-to-end publication honestly.
