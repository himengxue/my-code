# dsh-douyin-assistant

把本仓库的 [`douyin-assistant`](../douyin-assistant/README.md) skill 打包成一个 **DSH 插件**：
一份运行时技能 + 六个工具 + 一个设置页。执行器仍然是 skill 自带的本地 Python/Node 运行时，
插件只负责把它接进 DeepSeek Harness，不复制它的策略与账本逻辑。

## 贡献了什么

| 贡献 | 类型 | 说明 |
|---|---|---|
| 技能 `douyin-assistant` | `ctx.skills.register` | 以 `bundled` 运行时技能注册，模型在 `<available_skills>` 里直接看到；不再依赖 `~/.dsh/skills` 的文件拷贝 |
| `douyin_status` | 工具 | `version` / `doctor` / `policy` / `brief` / `jobs` / `auth-status` |
| `douyin_topic` | 工具 | 写入本轮选题记录 |
| `douyin_render` | 工具 | 分镜 → 720×1280 / 25fps / 无声 H.264 文字动画 + 封面 + `publish.json` |
| `douyin_video` | 工具 | `mine` / `prepare` / `publish` |
| `douyin_comment` | 工具 | `list` / `prepare` / `send`（定向回复） |
| `douyin_browser` | 工具 | `open` / `snapshot` / `screenshot` / `click` / `fill`（发布页的 AI 声明、公开可见） |
| 设置页 | 客户端 | 设置 → 抖音助手：五个开关，直连 `ctx.configForms`，保存即生效 |

所有工具返回执行器原样的 JSON。`policy.json` 授权、去重键、`dispatched/confirmed` 账本仍由执行器决定，
插件既不复制这些判断，也不会放宽它们。

## 安装

前提：DSH 0.2.0-rc.2 及以上，Node ≥22.19 或 ≥24，Python 3.12（执行器自带 venv）。

```powershell
# 1) 安装插件自己的依赖（@deepseek-ai/schemastery 用于设置 schema）
cd dsh-plugin
pnpm install --prod

# 2) 绑定执行器：复制示例并写入你的 runtime 目录（含 agent.py 与 .venv）
Copy-Item assets\runtime.example.json assets\runtime.json
#   { "home": "D:\\path\\to\\douyin-assistant\\runtime" }

# 3) 装进 profile
dsh plugin --profile desktop add "<本目录的绝对路径>"
```

`dsh plugin add` 会把包链接进 profile，并把 `dsh-douyin-assistant` 加入 `dsh.profile.bundles`。
之后重启应用（或在插件页把它关掉再打开）即可加载。

执行器绑定优先级：环境变量 `DOUYIN_AGENT_RUNTIME` → `assets/runtime.json` →
`~/.dsh/skills/douyin-assistant/runtime.json`。找不到执行器时插件只打警告，不注册工具，不影响宿主启动。

## 设置

**设置 → 抖音助手**（左侧导航独立一项）与 **插件 → dsh-douyin-assistant 详情页** 改的是同一份 Host 配置。

| 字段 | 默认 | 作用 |
|---|---|---|
| `enabled` | true | 总开关：关闭后除只读状态外的工具都拒绝执行，不打开浏览器 |
| `publishVideos` | true | 允许 `douyin_video` 的 `prepare` / `publish` |
| `autoComment` | true | 允许 `douyin_comment` 的 `prepare` / `send`；`list` 不受影响 |
| `maxRepliesPerRun` | 5 | 本次运行最多发送几条回复，0 表示只准备不发送 |
| `headed` | true | 需要新开浏览器时用有头模式，减少风控验证页 |

字段都是 `.volatile()`：保存后不重载插件，工具在每次调用时读取当前值。被拒绝时返回
`{"ok": false, "error": {"code": "publish_disabled", "message": "…"}}`。

## 结构

```
cordis.patch.yml        bundle 补丁：插入 id=douyin-assistant 的 loader 条目
lib/index.js            宿主半边：运行时技能 + 六个工具 + Config schema
lib/client.js           浏览器半边：设置页（lazy-CJS 工厂，require('react') 走外壳共享表）
assets/SKILL.md         插件版技能正文（用工具，不拼命令行）
assets/references/      原 skill 的命令与验证说明
assets/runtime.example.json  执行器绑定模板（真正的 runtime.json 不入库）
tools/smoke.mjs         宿主半边冒烟：注册的工具、schema、真实执行器调用
tools/client-smoke.mjs  浏览器半边冒烟：插槽注册与页面渲染
```

## 测试

```powershell
node tools/smoke.mjs          # 需要执行器可用；会真实调用 version/policy/video mine
node tools/client-smoke.mjs   # 纯本地：伪造 module loader 与 React
```

## 边界

- 设置开关只会让权限**更窄**：关掉不会绕过执行器 `policy.json`，打开也不会跳过 `dispatched/confirmed` 账本。
- 评论发送会触发平台的短信核验，需要本人在场；定时轮次不自动发送评论。
- 定时运行依赖 DSH 应用常开：提醒投递到原会话，应用关闭期间不执行。

## 许可

MIT，见仓库根目录 [`LICENSE`](../douyin-assistant/LICENSE)。被包装的 skill 与上游 `douyin-skills`
遵循 `douyin-assistant/THIRD_PARTY.md` 的署名与许可。
