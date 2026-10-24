# Local release audit — 2026-10-24

## Evidence

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

## Remaining limits

Current sandbox cannot launch CLI Chromium safely; CUA browser login is a separate path, not integrated into this runtime. Actual upload/publication/review/comment reply remain unverified. Windows launcher/manual setup are retained but not tested here; macOS is unverified. Fresh dependency installation was not performed; tests used an existing isolated Python installation. See README.md and SECURITY.md before running.

MANIFEST.sha256 inventories every source file except itself. The enclosing ZIP has a separate SHA256SUMS.txt beside it. No installed dependencies or generated runtime state are part of either manifest or archive.
