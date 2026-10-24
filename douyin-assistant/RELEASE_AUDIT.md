# Local release audit — 2026-10-24

## Original source preparation evidence (historical, before live validation)

- Included licenses: unchanged original MIT (douyin-agent contributors) and vendored MIT (zJay).
- Source copied using a positive allow-list into a new release directory; no live runtime directory was archived wholesale.
- 15/15 unittest cases passed: 12 offline behavior and 3 security cases.
- Node syntax check for cdp_client.mjs passed.
- Relocated POSIX launcher test passed in a directory containing spaces; HOME/state/cache remain project-local and CHROME_BIN override is preserved. Test used a harmless stub interpreter, not Chromium.
- Relative skill binding and explicit Markdown file links validated.
- Candidate render smoke test: 4 seconds, 720×1280, silent H.264; full FFmpeg decode passed; no publishing. Test outputs were temporary and removed.
- Staged text scan found no matches for private keys, GitHub/API/AWS tokens, literal bearer credentials or personal workspace paths. Pattern checks are not proof that all possible secrets are absent; allow-list exclusion is the primary safeguard.
- Three existing Python SyntaxWarnings in vendored publish.py (invalid escape sequence) were observed; tests passed. No upstream browser or live-account integration test was run.
- No GitHub writes, account login, publishing, or paid network operation performed for this preparation.

## Excluded inventory (categories only; contents not inspected)

Excluded from live runtime: data/ (HOME, browser profile, account state, databases and locks), policy.json, .venv/, node_modules/, __pycache__/ and cache/.
Excluded from source surroundings: .private/ quarantine, checks/ raw logs/screenshots/media/results, original installer/backups and machine-specific runtime.json.
Excluded generated assets: videos, audio, voice references, artwork, screenshots and other binary outputs.
Excluded obsolete sharing/install scripts that download portable runtimes or register global skills; this release documents manual isolated installation instead.
Included only placeholder/unconfigured policy.example.json; no local user's authorization or credentials.

## Original remaining limits (historical)

Current sandbox cannot launch CLI Chromium safely; CUA browser login is a separate path, not integrated into this runtime. Actual upload/publication/review/comment reply remain unverified. Windows launcher/manual setup are retained but not tested here; macOS is unverified. Fresh dependency installation was not performed; tests used an existing isolated Python installation. See README.md and SECURITY.md before running.

MANIFEST.sha256 inventories every source file except itself. The enclosing ZIP has a separate SHA256SUMS.txt beside it. No installed dependencies or generated runtime state are part of either manifest or archive.

## Windows CLI retest and compatibility patch — 2026-10-24

Base commit: `098372dfe7603259d5ab1d04ebf78fb8d845fd60`. The original checkout was kept unchanged. A separate local test copy received reversible source patches; the candidate for publication was exported with a positive source allow-list, never by archiving the live runtime.

Environment: Windows 11 x64, OS build 26200; Python 3.12.15; Node 24.21.0 / npm 11.19.0; Edge 155.0.4283.62; Pillow 13.0.0, imageio-ffmpeg 0.6.0, ws 8.21.3. Existing Python/Node/browser were reused; official dependencies were installed in the isolated test directory. Profile/process arguments were checked before login; CDP stayed on loopback and browser sandbox flags were not weakened. Original 57 manifest entries match after normalizing the Git checkout's CRLF line endings to LF.

Actual video: an original silent 13-second text/shape joke, 720×1280 at 25 fps, created with the CLI renderer and fully decoded. No third-party media or paid service was used. Video SHA-256: `8b03325b159319bccc645b3d30695db20a3df28207508aa9250aa7ab73bb6e64`. The media itself is excluded from the repository.

- The human completed the new isolated browser login. CLI auth and self-account checks then succeeded; no existing browser Cookie was read or copied.
- One prepare/upload and one final publish were performed. The title/caption/file hashes, cover, public visibility and AI declaration were checked before the final action.
- Submission response at **2026-10-24 11:01:10.767 UTC**: success/submitted. Creator management at **11:03:22.522 UTC**: published. Public detail at **11:04:49.251 UTC**: the test video and its AI declaration were visible. These are separate observations, not an inference that every submitted video is public.
- Public test result: https://www.douyin.com/video/7700187718818532617 . Its comments were empty. One genuine existing sticker comment on a different owned video was read for the reply test; no comments were fabricated.

### Reply correction: blocked, not successful

The reply command clicked once at **2026-10-24 11:13:49.917 UTC** and incorrectly returned `confirmed`. The saved screenshot instead shows an SMS identity-verification overlay and the draft still in the inline editor. A subsequent reload did not show that reply. The platform outcome is **blocked by SMS verification**, with no durable reply confirmed. The original response/screenshot/ledger are preserved locally and an outcome correction is recorded; no audit record is deleted or relabeled to hide the error.

The defect had two causes: verification detection omitted this SMS overlay, and disabled `contenteditable=false` draft text survived the previous editor exclusion. The patch detects that overlay, excludes all marked/disabled editors, checks target author/key and scopes send controls to the target card. Post-click verification is stored as uncertain with `needs_user_verification` and `retry_safe=false`. Even an empty-editor/current-page reply echo now remains uncertain and requests independent verification; it is not proof of remote persistence. No repeat click or verification bypass was attempted, and the patched real successful-reply path remains untested.

### Candidate regression and DSH evidence

- **37/37 unittest** on Windows in the clean, unconfigured source export. Includes default denial, durable no-redispatch, terminal marker handling, own-card ambiguity, profile isolation/fallback, reply verification outcomes and six skill-binding/relocation checks. Linux/Windows platform values and root/non-root UID values are simulated for launch-flag safety; this is not a Linux browser run.
- **12/12 about:blank DOM checks** using the same approved isolated browser: wrong author/key rejection, unique editor, scoped input/send, draft exclusion including hidden/disabled editors, unrelated preview exclusion and SMS stop. No platform content was sent by this test.
- **11/11 actual installed DSH host-loader checks**: `0.2.0-rc.2`, real Cordis Context with only SkillRegistry/SkillFileSystem, `ctx.skills.list/get`, whole repository/nested cwd/standalone package discovery and loading, source/path/resourceBase assertions, Chinese/space paths and explicit canonical/runtime resolution. Plugin fibers were disposed. Desktop's embedded Node reported 24.18.1. Synthetic filesystem fixtures and empty user skill roots were used, with no model API, credentials or model session. Official sources were reviewed at `639ed015397290b3745d163aafe02ffee4aa3f84` (rc.2) and `22ddee3792402c3e70ec5f86a63c3e3e895a2f60` (rc.3); version-specific Node requirements are documented separately.
- Node syntax checks pass for the existing CDP bridge and the optional DSH component smoke script. Existing vendored Python escape warnings are unchanged.
- A first test attempt hit an environment-specific SQLite temporary-directory access error. Re-running with process-local TEMP/TMP inside the writable task directory succeeded; no global setting or sandbox was disabled.

### Publication contents and remaining limits

Source changes: `runtime/agent.py`, `runtime/runtime.py`, vendored `chrome_launcher.py` and `douyin/interact.py`, portable security/new regression tests, a root skill router, read-only binding resolver and factual documentation. MIT and upstream attribution remain intact; no new runtime dependency was introduced. The DSH router contains no second implementation or runtime binding.

Only audited source/tests/docs are included. Exclusions remain: credentials, account/profile/Cookie data, local policy, SQLite databases, logs, screenshots, generated media, venv/node_modules, fixtures and personal absolute paths. The updated MANIFEST.sha256 covers LF-normalized source files within `douyin-assistant/`, except the manifest itself; the outer repository README/root skill router are outside that package inventory. No new ZIP is implied by this patch.

Still unverified: successful persistent real reply after human verification; full DSH model-session execution and sandbox/browser/loopback capability; macOS/other Windows builds; live Linux browser. Fixed-port profile ownership, unstable comment-key fallback and advisory policy limits are documented in SECURITY.md. Do not advertise general unattended production readiness or end-to-end DSH publishing from this evidence.
