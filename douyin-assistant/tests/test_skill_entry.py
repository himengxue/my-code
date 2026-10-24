"""Offline relocation/binding checks, not a DSH model-session integration test."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent
SPEC = importlib.util.spec_from_file_location('resolve_runtime', PROJECT/'tools/resolve_runtime.py')
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


class SkillEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='skill entry ')
        self.root = Path(self.temporary.name)/'中文 空格目录'

    def tearDown(self):
        self.temporary.cleanup()

    def copy_package(self, target):
        for name in ('.agents/skills/douyin-assistant/SKILL.md', '.agents/skills/douyin-assistant/runtime.json',
                     'runtime/douyin-agent', 'runtime/douyin-agent.cmd', 'tools/resolve_runtime.py'):
            destination = target/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT/name, destination)
        return target/'.agents/skills/douyin-assistant/SKILL.md'

    def test_standalone_package_binding(self):
        skill = self.copy_package(self.root)
        result = resolver.resolve_runtime(skill)
        self.assertEqual(Path(result['runtime_dir']), self.root/'runtime')

    def test_whole_repository_entry_points_to_canonical_skill(self):
        source = REPOSITORY/'.agents/skills/douyin-assistant/SKILL.md'
        if not source.is_file():
            self.skipTest('whole-repository wrapper is absent in standalone package')
        skill = self.copy_package(self.root/'douyin-assistant')
        wrapper = self.root/'.agents/skills/douyin-assistant/SKILL.md'
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
        target = re.search(r'\[完整技能\]\(([^)]+)\)', wrapper.read_text(encoding='utf-8')).group(1)
        self.assertEqual((wrapper.parent/target).resolve(), skill)
        self.assertEqual(Path(resolver.resolve_runtime(skill)['runtime_dir']), self.root/'douyin-assistant/runtime')

    def test_cli_resolves_independently_of_cwd(self):
        self.copy_package(self.root)
        result = subprocess.run([sys.executable, str(self.root/'tools/resolve_runtime.py')],
                                cwd=self.temporary.name, capture_output=True, encoding='utf-8', check=True)
        self.assertTrue(json.loads(result.stdout)['ok'])
        self.assertFalse((self.root/'runtime/data').exists())

    def test_missing_runtime_returns_json_and_nonzero(self):
        self.copy_package(self.root)
        (self.root/'runtime/douyin-agent.cmd').unlink()
        result = subprocess.run([sys.executable, str(self.root/'tools/resolve_runtime.py')],
                                capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'runtime_binding_invalid')

    def test_missing_binding_fails(self):
        skill = self.copy_package(self.root)
        skill.with_name('runtime.json').unlink()
        with self.assertRaisesRegex(ValueError, 'runtime.json is missing'):
            resolver.resolve_runtime(skill)

    def test_entrypoint_cannot_escape_runtime(self):
        skill = self.copy_package(self.root)
        file = skill.with_name('runtime.json')
        binding = json.loads(file.read_text())
        binding['entrypoint'] = '../tools/resolve_runtime.py'
        file.write_text(json.dumps(binding), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'outside the runtime'):
            resolver.resolve_runtime(skill)
