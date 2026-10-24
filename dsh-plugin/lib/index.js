// dsh-douyin-assistant — host half.
//
// The douyin-assistant project (github.com/himengxue/my-code) ships a Markdown
// skill plus a local Python executor. Dropping it into ~/.dsh/skills works, but
// then nothing tells the model *how* to reach the executor besides prose, and
// every command goes through a shell. This plugin keeps the same instructions
// as a runtime skill and adds typed tools that drive the executor directly:
//
//   ctx.skills  one runtime skill entry ("douyin-assistant")
//   ctx.tools   douyin_status / douyin_topic / douyin_render / douyin_video /
//               douyin_comment / douyin_browser
//
// Deliberate constraints:
//   * No imports outside node:*. The host supplies `tools`/`skills` through
//     ctx; `defineTool` would only buy argument validation we do by hand, at
//     the cost of a runtime dependency on @deepseek-ai/dsh-tools.
//   * The executor is spawned as a child process (`.venv` python + agent.py),
//     mirroring runtime/douyin-agent.cmd: PYTHONUTF8, DOUYIN_AGENT_HOME and
//     HOME are the three variables that launcher sets.
//   * Every tool returns the executor's own JSON verbatim. The executor already
//     owns policy checks, dedupe keys and the dispatched/confirmed ledger, so
//     the plugin must never re-implement or shortcut those decisions.
import { execFile } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import z from '@deepseek-ai/schemastery'

export const name = 'douyin-assistant'
export const inject = ['tools', 'skills']

/**
 * Profile-owned settings, declared rather than registered: a settings namespace
 * IS a plugin entry, so the Plugins page renders this schema for the
 * `douyin-assistant` row. Every field is `.volatile()` — the page can change it
 * live without remounting the plugin, and each tool call reads the current
 * value through `Volatile#get()`.
 *
 * The gate only ever narrows what the executor's own policy.json already
 * allows. Turning a switch off cannot grant new authority, and turning one on
 * cannot bypass the executor's authorization or its dispatched/confirmed ledger.
 */
/**
 * Mark a field live when the running Schemastery supports it. DSH 0.2.0-rc.2
 * ships 3.18.4 where `.volatile()` exists; an older host copy would silently
 * drop the flag, so the fallback keeps the plugin loadable instead of throwing.
 */
const live = (schema) => (typeof schema.volatile === 'function' ? schema.volatile() : schema)

export const Config = z.object({
  enabled: live(
    z
      .boolean()
      .default(true)
      .description('总开关：关闭后除只读状态外的工具都拒绝执行，不打开浏览器、不发布、不回复'),
  ),
  publishVideos: live(
    z.boolean().default(true).description('允许上传并发布视频（douyin_video 的 prepare / publish）'),
  ),
  autoComment: live(
    z
      .boolean()
      .default(true)
      .description('允许自动回复本人作品下的评论（douyin_comment 的 prepare / send），读取列表不受影响'),
  ),
  maxRepliesPerRun: live(
    z
      .number()
      .min(0)
      .max(5)
      .step(1)
      .default(5)
      .description('本次运行最多发送的回复条数，0 表示只准备不发送'),
  ),
  headed: live(
    z
      .boolean()
      .default(true)
      .description('需要新开浏览器时使用有头模式，减少风控验证页（已有浏览器时自动附着，不受影响）'),
  ),
})

const HERE = dirname(fileURLToPath(import.meta.url))
const ASSETS = resolve(HERE, '..', 'assets')
const SKILL_FILE = join(ASSETS, 'SKILL.md')
const BINDING_FILE = join(ASSETS, 'runtime.json')

function readJson(file) {
  try {
    return JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''))
  } catch {
    return undefined
  }
}

function exists(file) {
  try {
    readFileSync(file)
    return true
  } catch {
    return false
  }
}

/**
 * Resolve the executor directory. Order: explicit environment override, the
 * package's own binding, then the user-level skill copy so a plugin installed
 * next to an existing skill install keeps working without editing assets.
 */
function resolveRuntime() {
  const candidates = []
  if (process.env.DOUYIN_AGENT_RUNTIME) candidates.push(process.env.DOUYIN_AGENT_RUNTIME)
  const binding = readJson(BINDING_FILE)
  if (binding && typeof binding.home === 'string') candidates.push(binding.home)
  const home = process.env.USERPROFILE || process.env.HOME
  if (home) {
    const skillDir = join(home, '.dsh', 'skills', 'douyin-assistant')
    const userBinding = readJson(join(skillDir, 'runtime.json'))
    if (userBinding && typeof userBinding.home === 'string') candidates.push(resolve(skillDir, userBinding.home))
  }
  for (const dir of candidates) {
    if (dir && exists(join(dir, 'agent.py'))) return resolve(dir)
  }
  throw new Error(
    '找不到抖音执行器：请在 assets/runtime.json 写入 {"home":"<runtime 目录>"}，或设置 DOUYIN_AGENT_RUNTIME',
  )
}

function parseSkill(markdown) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(markdown)
  const frontmatter = match ? match[1] : ''
  const body = match ? markdown.slice(match[0].length) : markdown
  const description = /^description:\s*(.+)$/m.exec(frontmatter)?.[1]?.trim().replace(/^['"]|['"]$/g, '')
  return { description, content: body.trimStart() }
}

/**
 * Append one line to assets/apply.log. A packaged plugin has no console the
 * user can read, so activation and skill-registration outcome has to be
 * observable from disk. Never throws: diagnostics must not affect boot.
 */
function trace(line) {
  try {
    mkdirSync(ASSETS, { recursive: true })
    writeFileSync(join(ASSETS, 'apply.log'), `${new Date().toISOString()} pid=${process.pid} ${line}\n`, { flag: 'a' })
  } catch {
    // ignore
  }
}

function makeRunner(runtime) {
  const python =
    process.platform === 'win32'
      ? join(runtime, '.venv', 'Scripts', 'python.exe')
      : join(runtime, '.venv', 'bin', 'python')
  const agent = join(runtime, 'agent.py')
  return (args, { timeoutMs = 600_000 } = {}) =>
    new Promise((resolveRun) => {
      execFile(
        python,
        [agent, ...args],
        {
          cwd: runtime,
          env: {
            ...process.env,
            PYTHONUTF8: '1',
            DOUYIN_AGENT_HOME: join(runtime, 'data'),
            HOME: join(runtime, 'data', 'home'),
          },
          timeout: timeoutMs,
          maxBuffer: 32 * 1024 * 1024,
          windowsHide: true,
        },
        (error, stdout, stderr) => {
          const out = String(stdout ?? '').trim()
          const parse = (text) => {
            try {
              return JSON.parse(text)
            } catch {
              return undefined
            }
          }
          let value = parse(out)
          if (value === undefined) {
            const last = out.split(/\r?\n/).filter(Boolean).pop()
            value = last === undefined ? undefined : parse(last)
          }
          if (value !== undefined) {
            resolveRun(value)
            return
          }
          resolveRun({
            ok: false,
            error: {
              code: 'executor_no_json',
              message: error ? String(error.message) : '执行器没有返回 JSON',
              stderr: String(stderr ?? '').slice(-4000),
            },
          })
        },
      )
    })
}

function asText(value) {
  return [{ type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value, null, 2) }]
}

/** Read a possibly-volatile config field, falling back when the loader supplied a plain value. */
function setting(value, fallback) {
  if (value && typeof value.get === 'function') {
    const current = value.get()
    return current === undefined ? fallback : current
  }
  return value === undefined ? fallback : value
}

/** Structured refusal in the executor's own result shape, so callers parse it the same way. */
function blocked(code, message) {
  return { ok: false, error: { code, message } }
}

function withHeaded(args, settings) {
  return settings.headed ? ['--headed', ...args] : args
}

/** Raw registry definition: same fields defineTool() would produce, minus the dependency. */
function define(definition) {
  return {
    ...definition,
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => asText(value),
    },
  }
}

function assertString(value, field) {
  if (typeof value !== 'string' || value.trim() === '') throw new Error(`${field} 需要非空字符串`)
  return value
}

function writeTemporary(name, text) {
  const dir = join(tmpdir(), 'dsh-douyin-assistant')
  mkdirSync(dir, { recursive: true })
  const file = join(dir, `${name}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`)
  writeFileSync(file, text, 'utf8')
  return file
}

function buildTools(run, readSettings, replyBudget) {
  const status = define({
    name: 'douyin_status',
    description:
      '抖音自主创作者执行器的只读状态：version/doctor 环境自检，policy 当前运营范围，brief 简报，jobs 历史任务账本，auth-status 登录态与风控页。先看 ok，再看 data。',
    parameters: {
      type: 'object',
      properties: {
        command: {
          type: 'string',
          enum: ['version', 'doctor', 'policy', 'brief', 'jobs', 'auth-status'],
          description: '要查询的状态项',
        },
      },
      required: ['command'],
      additionalProperties: false,
    },
    async execute(args) {
      const command = assertString(args.command, 'command')
      const settings = readSettings()
      const readOnly = ['version', 'doctor', 'policy', 'brief', 'jobs'].includes(command)
      if (!settings.enabled && !readOnly) {
        return blocked('plugin_disabled', '插件已在设置中关闭（enabled=false），auth-status 需要浏览器，已拒绝')
      }
      if (command === 'auth-status') {
        return run(withHeaded(['auth', 'status'], settings), { timeoutMs: 180_000 })
      }
      return run([command], { timeoutMs: 180_000 })
    },
  })

  const topic = define({
    name: 'douyin_topic',
    description:
      '把本轮自主选题写入执行器账本（topic 任务）。需要 title、audience、angle、why_now、difference_from_recent_posts，可带 sources/internal_candidates/selected。选题由你完成，执行器只记账。',
    parameters: {
      type: 'object',
      properties: {
        topic: {
          type: 'object',
          description: '选题对象，字段见描述',
          additionalProperties: true,
        },
      },
      required: ['topic'],
      additionalProperties: false,
    },
    async execute(args) {
      const payload = args.topic
      if (!readSettings().enabled) return blocked('plugin_disabled', '插件已在设置中关闭（enabled=false）')
      if (!payload || typeof payload !== 'object') throw new Error('topic 需要对象')
      const file = writeTemporary('topic', JSON.stringify(payload, null, 2))
      return run(['topic', '--file', file], { timeoutMs: 120_000 })
    },
  })

  const render = define({
    name: 'douyin_render',
    description:
      '用内置渲染器把分镜渲染成 720x1280 / 25fps / 无声 H.264 原创文字动画，并输出封面、caption.txt 和 publish.json。storyboard 需含 title 与 2-12 个 scenes（每个 headline/body/duration 2-30 秒）；out 必须是不存在的目录。也是发布前的自检：文字过长会被拒绝。',
    parameters: {
      type: 'object',
      properties: {
        storyboard: { type: 'object', description: '分镜对象', additionalProperties: true },
        out: { type: 'string', description: '输出目录（必须不存在）' },
      },
      required: ['storyboard', 'out'],
      additionalProperties: false,
    },
    async execute(args) {
      const storyboard = args.storyboard
      if (!readSettings().enabled) return blocked('plugin_disabled', '插件已在设置中关闭（enabled=false）')
      if (!storyboard || typeof storyboard !== 'object') throw new Error('storyboard 需要对象')
      const out = resolve(assertString(args.out, 'out'))
      mkdirSync(dirname(out), { recursive: true })
      const file = writeTemporary('storyboard', JSON.stringify(storyboard, null, 2))
      return run(['render', '--storyboard', file, '--out', out], { timeoutMs: 900_000 })
    },
  })

  const video = define({
    name: 'douyin_video',
    description:
      '视频发布流水线。mine 读取本人创作者中心已加载作品；prepare 上传并填写标题/简介/封面，返回 job 与 target_id（之后要用 browser 工具设置 AI 声明与公开可见）；publish 核对表单和设置后真正点击发布，结果记为 confirmed/uncertain。publish 不可重复执行。',
    parameters: {
      type: 'object',
      properties: {
        action: { type: 'string', enum: ['mine', 'prepare', 'publish'] },
        limit: { type: 'number', description: 'mine 的条数，默认 20' },
        manifest: { type: 'string', description: 'prepare 需要的 publish.json 路径' },
        job: { type: 'string', description: 'publish 需要的任务 id' },
      },
      required: ['action'],
      additionalProperties: false,
    },
    async execute(args) {
      const action = assertString(args.action, 'action')
      const settings = readSettings()
      if (!settings.enabled) return blocked('plugin_disabled', '插件已在设置中关闭（enabled=false）')
      if (action === 'mine') {
        return run(withHeaded(['video', 'mine', '--limit', String(Math.max(1, Math.min(Number(args.limit) || 20, 100)))], settings), {
          timeoutMs: 300_000,
        })
      }
      if (!settings.publishVideos) {
        return blocked('publish_disabled', '设置里关闭了发布视频（publishVideos=false）；打开该开关，或让用户在设置里授权后再试')
      }
      if (action === 'prepare') {
        return run(withHeaded(['video', 'prepare', '--manifest', assertString(args.manifest, 'manifest')], settings), {
          timeoutMs: 900_000,
        })
      }
      return run(withHeaded(['video', 'publish', '--job', assertString(args.job, 'job')], settings), { timeoutMs: 900_000 })
    },
  })

  const comment = define({
    name: 'douyin_comment',
    description:
      '评论与定向回复。list 读取本人某条视频下可见评论并返回用于精确定位的 key；prepare 进入该作者的回复模式并填入回复（不发送）；send 真正发送并核对。同一评论发送后不可重发，回显不等于远端成功。',
    parameters: {
      type: 'object',
      properties: {
        action: { type: 'string', enum: ['list', 'prepare', 'send'] },
        video: { type: 'string', description: 'list 需要的视频 id' },
        limit: { type: 'number', description: 'list 条数，默认 20' },
        key: { type: 'string', description: 'prepare 需要的评论 key' },
        text: { type: 'string', description: 'prepare 的回复正文（UTF-8 文本）' },
        job: { type: 'string', description: 'send 需要的任务 id' },
      },
      required: ['action'],
      additionalProperties: false,
    },
    async execute(args) {
      const action = assertString(args.action, 'action')
      const settings = readSettings()
      if (!settings.enabled) return blocked('plugin_disabled', '插件已在设置中关闭（enabled=false）')
      if (action === 'list') {
        const video = assertString(args.video, 'video')
        const limit = Math.max(1, Math.min(Number(args.limit) || 20, 50))
        return run(withHeaded(['comment', 'list', '--video', video, '--limit', String(limit)], settings), {
          timeoutMs: 300_000,
        })
      }
      if (!settings.autoComment) {
        return blocked('auto_comment_disabled', '设置里关闭了自动回复（autoComment=false）；打开该开关，或让用户在设置里授权后再试')
      }
      if (action === 'prepare') {
        const file = writeTemporary('reply', `${assertString(args.text, 'text')}\n`)
        return run(withHeaded(['comment', 'prepare', '--key', assertString(args.key, 'key'), '--text-file', file], settings), {
          timeoutMs: 300_000,
        })
      }
      if (!replyBudget.take(Number(settings.maxRepliesPerRun))) {
        return blocked(
          'reply_budget_exhausted',
          `本次运行已发送 ${replyBudget.sent()} 条回复，达到设置上限 maxRepliesPerRun=${settings.maxRepliesPerRun}；提高上限或重启应用后再试`,
        )
      }
      return run(withHeaded(['comment', 'send', '--job', assertString(args.job, 'job')], settings), { timeoutMs: 300_000 })
    },
  })

  const browser = define({
    name: 'douyin_browser',
    description:
      '执行器自带浏览器（loopback CDP）。open 打开抖音页面；snapshot 读取当前页面文本与可点击节点 id；screenshot 存图；click 点普通控件（禁止发布/发送等提交控件）；fill 只填空输入框或核对同文。发布页的 AI 声明、公开可见用它设置。',
    parameters: {
      type: 'object',
      properties: {
        action: { type: 'string', enum: ['open', 'snapshot', 'screenshot', 'click', 'fill'] },
        url: { type: 'string', description: 'open 需要的 https://www.douyin.com/... 地址' },
        target: { type: 'string', description: '页面 target id' },
        node: { type: 'string', description: 'snapshot 返回的节点 id' },
        text: { type: 'string', description: 'fill 的文本' },
      },
      required: ['action'],
      additionalProperties: false,
    },
    async execute(args) {
      const action = assertString(args.action, 'action')
      const settings = readSettings()
      if (!settings.enabled) return blocked('plugin_disabled', '插件已在设置中关闭（enabled=false），浏览器操作已拒绝')
      const target = args.target === undefined ? undefined : String(args.target)
      if (action === 'open') {
        return run(withHeaded(['browser', 'open', '--url', assertString(args.url, 'url')], settings), { timeoutMs: 180_000 })
      }
      if (action === 'snapshot' || action === 'screenshot') {
        return run(withHeaded(['browser', action, '--target', assertString(target, 'target')], settings), {
          timeoutMs: 180_000,
        })
      }
      if (action === 'click') {
        return run(
          withHeaded(['browser', 'click', '--target', assertString(target, 'target'), '--node', assertString(args.node, 'node')], settings),
          { timeoutMs: 180_000 },
        )
      }
      const file = writeTemporary('fill', `${assertString(args.text, 'text')}\n`)
      return run(
        withHeaded(
          ['browser', 'fill', '--target', assertString(target, 'target'), '--node', assertString(args.node, 'node'), '--text-file', file],
          settings,
        ),
        { timeoutMs: 180_000 },
      )
    },
  })

  return [status, topic, render, video, comment, browser]
}

export function apply(ctx, config = {}) {
  const readSettings = () => ({
    enabled: setting(config.enabled, true) !== false,
    publishVideos: setting(config.publishVideos, true) !== false,
    autoComment: setting(config.autoComment, true) !== false,
    maxRepliesPerRun: Math.max(0, Math.min(Number(setting(config.maxRepliesPerRun, 5)) || 0, 5)),
    headed: setting(config.headed, true) !== false,
  })

  // Per-process reply budget: the executor owns the durable ledger and the
  // platform limit, this counter is only the user's own ceiling for one run.
  let repliesSent = 0
  const replyBudget = {
    sent: () => repliesSent,
    take(max) {
      if (!Number.isFinite(max) || max <= 0 || repliesSent >= max) return false
      repliesSent += 1
      return true
    },
  }

  trace(`apply start | inject=${JSON.stringify(inject)} tools=${typeof ctx.tools?.register} skills=${typeof ctx.skills?.register} settings=${JSON.stringify(readSettings())}`)
  ctx.on?.('loader/volatile-update', () => trace(`settings updated | ${JSON.stringify(readSettings())}`))

  // The skill is the cheap half: register it even when the executor binding is
  // missing, so the instructions (and their repair hints) still reach the model.
  try {
    const { description, content } = parseSkill(readFileSync(SKILL_FILE, 'utf8'))
    ctx.skills.register({
      name: 'douyin-assistant',
      description: description || '抖音自主创作者：选题、原创短视频、发布与评论回复的本地执行器。',
      content,
      source: 'bundled',
      metadata: { version: '2.0.0', origin: 'douyin-agent' },
      resourceBase: { kind: 'directory', path: ASSETS },
    })
    trace(`skill registered | chars=${content.length} | description=${String(description).slice(0, 24)}`)
  } catch (error) {
    trace(`skill register FAILED | ${String(error?.message ?? error)}`)
    ctx.logger?.warn?.(`[douyin-assistant] 注册技能失败: ${String(error?.message ?? error)}`)
  }

  let runtime
  try {
    runtime = resolveRuntime()
  } catch (error) {
    // A missing executor must not take the profile down: the skill still
    // explains how to point the binding at a runtime directory.
    trace(`runtime missing | ${String(error?.message ?? error)}`)
    ctx.logger?.warn?.(`[douyin-assistant] ${String(error?.message ?? error)}`)
    return
  }
  const run = makeRunner(runtime)
  trace(`runtime resolved | ${runtime}`)

  const registered = []
  for (const definition of buildTools(run, readSettings, replyBudget)) {
    try {
      ctx.tools.register(definition)
      registered.push(definition.name)
    } catch (error) {
      trace(`tool register FAILED | ${definition.name} | ${String(error?.message ?? error)}`)
      ctx.logger?.warn?.(`[douyin-assistant] 注册 ${definition.name} 失败: ${String(error?.message ?? error)}`)
    }
  }
  trace(`tools registered | ${registered.join(',')}`)
}
