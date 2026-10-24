#!/usr/bin/env node
// Optional test of an explicitly supplied, already-installed official provider.
// No model API, DSH credentials, user skill roots, or browser access is used.
import { copyFile, lstat, mkdir, mkdtemp, readFile } from 'node:fs/promises';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const args = process.argv.slice(2);
const option = name => {
  const index = args.indexOf(name);
  if (index < 0 || !args[index + 1]) throw new Error(`Required option: ${name}`);
  return resolve(args[index + 1]);
};
const providerPath = option('--provider');
const registryPath = option('--registry');
const cordisPath = option('--cordis');
const temporaryRoot = option('--temp-dir');
const project = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repository = resolve(project, '..');
const fixture = await mkdtemp(join(temporaryRoot, 'dsh-discovery-'));
const whole = join(fixture, '整仓 有空格');
const standalone = join(fixture, '独立包 有空格');
const noGitPackage = join(fixture, '独立解压包 无Git');
const canonical = '.agents/skills/douyin-assistant/SKILL.md';
async function copy(source, destination) {
  await mkdir(dirname(destination), { recursive: true });
  await copyFile(source, destination);
}
await copy(join(repository, canonical), join(whole, canonical));
await copy(join(project, canonical), join(whole, 'douyin-assistant', canonical));
await copy(join(project, canonical), join(standalone, canonical));
await copy(join(project, canonical), join(noGitPackage, canonical));
for (const destination of [join(whole, 'douyin-assistant'), standalone, noGitPackage]) {
  for (const file of ['.agents/skills/douyin-assistant/runtime.json', 'runtime/douyin-agent', 'runtime/douyin-agent.cmd']) {
    await copy(join(project, file), join(destination, file));
  }
}
// Empty .git directories model only the documented discovery boundary.
await mkdir(join(whole, '.git'));
await mkdir(join(standalone, '.git'));
// This fixture must exercise cwd fallback, not inherit any ancestor Git root.
for (let directory = noGitPackage; ; directory = dirname(directory)) {
  let hasGit = false;
  try {
    await lstat(join(directory, '.git'));
    hasGit = true;
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  assert.equal(hasGit, false, 'The no-Git fixture requires --temp-dir outside every Git root');
  if (dirname(directory) === directory) break;
}
const SkillFileSystem = await import(pathToFileURL(providerPath).href);
const { default: SkillRegistry } = await import(pathToFileURL(registryPath).href);
const { Context } = await import(pathToFileURL(cordisPath).href);
const ctx = new Context();
const registryFiber = await ctx.plugin(SkillRegistry);
const providerFiber = await ctx.plugin(SkillFileSystem, {
  watch: false, dshHome: join(fixture, 'empty-dsh'),
  agentsHome: join(fixture, 'empty-agents'), bundledSkillDir: join(fixture, 'empty-bundled'),
});
const checks = {};
try {
  for (const [name, cwd, expected] of [
    ['whole_repository', whole, join(whole, canonical)],
    ['nested_cwd', join(whole, 'douyin-assistant'), join(whole, canonical)],
    ['standalone_package', standalone, join(standalone, canonical)],
    ['standalone_no_git', noGitPackage, join(noGitPackage, canonical)],
  ]) {
    const rows = await ctx.skills.list({ cwd });
    const candidates = rows.filter(row => row.name === 'douyin-assistant');
    assert.equal(candidates.length, 1);
    assert.equal(resolve(candidates[0].path), resolve(expected));
    checks[`${name}_discovered`] = true;
    const loaded = await ctx.skills.get('douyin-assistant', { cwd });
    assert.ok(loaded.content.length > 0);
    assert.equal(loaded.source, 'project-agents');
    assert.equal(resolve(loaded.path), resolve(expected));
    assert.equal(loaded.resourceBase.kind, 'directory');
    assert.equal(resolve(loaded.resourceBase.path), resolve(dirname(expected)));
    checks[`${name}_loaded`] = true;
    let canonicalPath = loaded.path;
    const isStandalone = name.startsWith('standalone_');
    if (!isStandalone) {
      const link = loaded.content.match(/\[完整技能\]\(([^)]+)\)/)?.[1];
      assert.ok(link);
      canonicalPath = resolve(dirname(loaded.path), link);
      const content = await readFile(canonicalPath, 'utf8');
      assert.ok(content.includes('runtime.json'));
      checks[`${name}_canonical_reachable`] = true;
    }
    const binding = JSON.parse(await readFile(join(dirname(canonicalPath), 'runtime.json'), 'utf8'));
    const runtime = resolve(dirname(canonicalPath), binding.home);
    assert.equal(runtime, isStandalone ? join(cwd, 'runtime') : join(whole, 'douyin-assistant/runtime'));
    assert.ok((await readFile(join(runtime, binding.windows_entrypoint), 'utf8')).includes('agent.py'));
    checks[`${name}_binding_resolved`] = true;
  }
} finally {
  await providerFiber.dispose();
  await registryFiber.dispose();
  // Keep only these synthetic text fixtures for inspection; no user data exists.
}
console.log(JSON.stringify({ ok: true, scope: 'installed Cordis Context + SkillRegistry + SkillFileSystem with local fixtures; not a model session', checks }));
