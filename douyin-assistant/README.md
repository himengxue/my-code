# 抖音自主创作者 Skill / Runtime

面向能运行本地命令的 Agent：自主选题、无声文字动画、浏览器操作和有持久记录的提交。**本修复候选已完成一次 Windows CLI 真实视频发布；评论发送被短信核验拦截，未完成成功回复验收。** 非抖音、OpenAI 或 DeepSeek 官方项目。

## 验证与平台

- Linux / Python 3.12：离线行为与安全回归测试可运行；本地文字动画渲染和解码可运行。
- 当前云沙箱无法启动 CLI 的 Chromium；不能靠关闭浏览器沙箱解决。另一路网页 CUA 登录不等于此 CLI 已登录、也没有与 CLI 集成。
- Windows 11 x64 build 26200、Python 3.12.15、Node 24.21.0、Edge 155.0.4283.62：隔离安装、人工扫码后 CLI 登录核对、原创渲染、上传与一次公开发布通过。详见 [验收矩阵](.agents/skills/douyin-assistant/references/validation.md)。
- 真实评论读取通过；定向发送触发短信身份核验。旧检测误将禁用编辑器中的草稿计为成功，修复后会停止并保留不确定状态。回复持久成功尚未验证，不要直接用于无人值守生产。
- DSH 已补齐整仓发现入口；已安装官方 provider 的离线发现/加载通过，完整 DSH 模型会话与沙箱内浏览器未测试。见 [DSH 兼容说明](DSH_COMPATIBILITY.md)。macOS 未验证。

## 手动安装

需要 Python 3.12、Node.js >=18、可安全运行的 Chrome/Chromium（Windows 也可 Edge），以及有合法使用权的中文字体。使用自己信任的软件来源安装；本仓库不含这些二进制。

在 `douyin-assistant/` 包根目录，Linux/POSIX：

```sh
python3 -m venv runtime/.venv
runtime/.venv/bin/python -m pip install -r runtime/requirements.txt
(cd runtime/vendor/douyin-skills-09e9ccb6c484c59d69e11dbb4bc975c47e5510e5 && npm ci --ignore-scripts --no-audit --no-fund)
./runtime/douyin-agent version
./runtime/douyin-agent doctor
./runtime/douyin-agent policy
```

Windows PowerShell（依赖同上；本次复用了已有 Python、Node 和 Edge，创建独立 venv）：

```powershell
py -3.12 -m venv runtime/.venv
& runtime/.venv/Scripts/python.exe -m pip install -r runtime/requirements.txt
Push-Location runtime/vendor/douyin-skills-09e9ccb6c484c59d69e11dbb4bc975c47e5510e5
npm ci --ignore-scripts --no-audit --no-fund
Pop-Location
& runtime/douyin-agent.cmd doctor
```

`CHROME_BIN` 可显式指定浏览器；`DOUYIN_FONT` 可指定中文字体。不要添加 `--no-sandbox` 或规避自动化检测的参数。缺少操作系统权限时请换用合法支持浏览器沙箱的环境，而不是绕过限制。

完整 skill 位于包内 `.agents/skills/douyin-assistant/SKILL.md`；整仓根另有轻量发现入口，只转到这份完整 skill。运行目录绑定相对于完整 skill 的 `runtime.json` 目录，不包含开发者路径；可用 `python tools/resolve_runtime.py` 检查。移动或独立安装 skill 时须更新本机绑定。

默认读 `runtime/policy.example.json`，发布和回复均禁用。只有取得当前用户明确授权后，才复制为 `runtime/policy.json` 并填写授权范围；不提交该文件。登录、验证码和平台验证由用户处理；未配置授权时不能发布或回复。未调用浏览器的 `doctor` 也可能报告缺少依赖/浏览器。

## 离线测试

```sh
runtime/.venv/bin/python -m unittest discover -s tests -v
```

Windows 使用 `.venv/Scripts/python.exe`。测试不登录、不发布、不下载依赖。渲染需 Pillow、FFmpeg 与中文字体；`references/commands.md` 中有分镜格式。

可选 `tests/browser_reply_smoke.py --port <明确的隔离 CDP 端口>` 只在 `about:blank` 上检查回复控件和短信弹窗，不向平台发送内容。默认 unittest 不连接浏览器；测试不要使用已授权生产目录中的 `policy.json`。本次 Windows 沙箱临时目录曾无法创建 SQLite 文件，改用任务目录内可写临时目录完成测试，未更改 sandbox 设置。

详见 [安全与隐私](SECURITY.md)、[变更记录](CHANGELOG.md)、[许可与来源](THIRD_PARTY.md) 和 skill 中的命令/验证说明。
