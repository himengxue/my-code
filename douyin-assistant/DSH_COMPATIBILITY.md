# DeepSeek Harness 兼容说明

本项目提供标准 Markdown skill 和共用 Python/Node 执行器，不是 DSH 插件或官方服务。Windows CLI 发布实测和 DSH 宿主测试是两项不同的证据。

正常使用需所选 DSH preset 已提供 skill provider/consumer。某些最简 preset 可能不含这些组件；本项目不自动改写用户 preset、权限或模型配置，也不假设存在 `dsh skills list`、`--offline` 等未文档化命令。

## 发现入口与唯一绑定

整仓 clone `my-code` 时，根目录 `.agents/skills/douyin-assistant/SKILL.md` 是轻量入口，只要求读取 `douyin-assistant/.agents/skills/douyin-assistant/SKILL.md`。完整操作说明和 `runtime.json` 只维护在后者；所有绑定路径相对该 JSON 文件解析。

单独取出 `douyin-assistant/` 时，从这个包的根目录启动 DSH，使用包内 `.agents/skills/`。如果放进另一个 Git 仓库，DSH 会以那个仓库为项目根；需要在那个根目录添加指向 canonical skill 的轻量入口，不能仅靠切换到子目录。不要只复制根入口而遗漏完整包。

此设计依据官方 [skills 文档](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/subsystems/skills.md) 和 [filesystem provider](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/skill/skill-filesystem/src/index.ts)，固定提交 `22ddee3792402c3e70ec5f86a63c3e3e895a2f60`：项目根取最近的 `.git`；扫描项目根的 `.agents/skills`，不递归搜索嵌套包。内部构造器的 `customSkillDirs` 不作为本项目的用户 CLI 配置建议。`agents/openai.yaml` 为可选展示信息。

## 运行要求

- DSH 本体按版本选择 Node：本机 `0.2.0-rc.2` 对应官方 [tag 提交](https://github.com/deepseek-ai/deepseek-harness/tree/639ed015397290b3745d163aafe02ffee4aa3f84)，其要求为 `^22.19.0 || >=24.0.0`；上述 `0.2.1-rc.3` 源码基线要求 >=24.9.0。rc.2 Desktop 可自带 DSH/Node，不需要为此升级。本项目浏览器 bridge 另需在执行器环境可调用的 `node` >=18，不能假定 Desktop 内嵌 Node 已在 PATH。
- 执行器需要 Python 3.12、项目 `.venv`、声明的依赖和可安全启动的 Chrome/Chromium/Edge。POSIX 使用 shell 启动器；Windows 从 PowerShell/pwsh 调用 `.cmd`。路径含空格时必须正确引用，PowerShell 使用 `&`。
- 宿主必须能运行本地命令、写入该 runtime 的 `data/`，并允许项目浏览器和 loopback CDP 通信。这是运行条件，不是放宽全局权限的建议。不得关闭 sandbox、隐藏自动化或复制日常浏览器登录态。
- 保留默认禁用发布/回复的策略；用户授权后才在本机配置。二维码、短信、验证码和协议由用户处理。遇风控停止相关操作。

从整仓根检查绑定：

```sh
python douyin-assistant/tools/resolve_runtime.py
```

独立包根目录则运行 `python tools/resolve_runtime.py`。该命令不启动浏览器、不读取模型凭证、不写登录态；缺少 canonical skill、绑定或入口时，返回 `ok=false` JSON 和退出码 2。根据返回的绝对入口路径运行 `version`、`doctor`、`policy`，不要根据当前 cwd 猜路径。依赖安装见 README。

JSON 完整返回后仍要检查 `ok`、任务状态与远端证据。非零退出码、输出截断、超时或后台任务句柄都不能证明没有发生提交；先等待原命令并核对 `jobs`/远端，不能重发。视频 `submitted` 不等于公开；回复当前页回显不等于远端持久成功。

## 2026-10-24 的实测边界

- 本机 `dsh --version` 实际返回 `0.2.0-rc.2`，与文档基线版本不同。
- 使用已安装 rc.2 的真实 Cordis Context，仅挂载 SkillRegistry 和 SkillFileSystem，以合成文件夹、空用户 skill 根、watch:false 完成 11 项 `ctx.skills.list/get` 检查：整仓、子目录 cwd、独立包、source/path/resourceBase、明确读取 canonical 链接并解析其 runtime 绑定。插件 fiber 在结束时释放。Desktop 内嵌 Node 实际为 24.18.1。测试未加载模型或用户凭证；这是离线 host-loader 测试，不是完整 DSH 会话。
- Python 测试覆盖中文/空格路径、绑定不依赖 cwd、缺失入口/绑定报错和入口越界拒绝。
- DSH 模型会话执行、其沙箱内 Python/浏览器/loopback、Windows named-pipe 能力：**not tested**。不能将这些待测条件写成已发生故障，也不能据此修改 sandbox。

可选组件复现脚本为 `tests/dsh_discovery_smoke.mjs`，接受显式的已安装模块文件路径 `--provider`、`--registry`、`--cordis` 和可写临时目录 `--temp-dir`。它不会安装 DSH，也不把内部测试构造参数当成用户配置入口。测试方法参照官方 [rc.2 filesystem 测试](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/skill/skill-filesystem/tests/skill-filesystem.spec.ts)，未复制其实现。默认 unittest 不需要 DSH。
