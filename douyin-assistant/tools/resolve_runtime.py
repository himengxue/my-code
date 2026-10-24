#!/usr/bin/env python3
"""Read the canonical skill binding without loading credentials or runtime state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CANONICAL = Path(__file__).resolve().parents[1] / '.agents/skills/douyin-assistant/SKILL.md'


def resolve_runtime(skill_file=CANONICAL):
    skill = Path(skill_file).resolve()
    if not skill.is_file():
        raise ValueError('canonical SKILL.md is missing')
    binding_file = skill.with_name('runtime.json')
    if not binding_file.is_file():
        raise ValueError('canonical runtime.json is missing')
    binding = json.loads(binding_file.read_text(encoding='utf-8-sig'))
    if not isinstance(binding, dict) or not isinstance(binding.get('home'), str) or not binding['home']:
        raise ValueError('runtime.json must contain a nonempty home string')
    home = (binding_file.parent / binding['home']).resolve()
    if not home.is_dir():
        raise ValueError('configured runtime directory is missing')
    entries = {}
    for key in ('entrypoint', 'windows_entrypoint'):
        value = binding.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f'runtime.json must contain {key}')
        entry = (home / value).resolve()
        if not entry.is_relative_to(home) or not entry.is_file():
            raise ValueError(f'{key} is missing or outside the runtime directory')
        entries[key] = str(entry)
    return {'skill_file': str(skill), 'runtime_dir': str(home), **entries}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-file', type=Path, default=CANONICAL)
    args = parser.parse_args(argv)
    try:
        result = {'ok': True, 'data': resolve_runtime(args.skill_file)}
    except (OSError, ValueError) as exc:
        result = {'ok': False, 'error': {'code': 'runtime_binding_invalid', 'message': str(exc)}}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
