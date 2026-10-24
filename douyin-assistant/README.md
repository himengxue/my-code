# 抖音自主创作者 Skill / Runtime

面向能运行本地命令的 Agent：自主选题、无声文字动画、浏览器操作和有持久记录的提交。**这是经过离线验证的源码候选版本，不是已完成真实账号发布验收的服务。** 非抖音、OpenAI 或 DeepSeek 官方项目。

## 验证与平台

- Linux / Python 3.12：离线行为与安全回归测试可运行；本地文字动画渲染和解码可运行。
- 当前云沙箱无法启动 CLI 的 Chromium；不能靠关闭浏览器沙箱解决。另一路网页 CUA 登录不等于此 CLI 已登录、也没有与 CLI 集成。
- Windows 10/11 x64：保留命令启动器和手动安装方法，此次未重新验证；macOS 未验证。
- 未完成真实账号上传、公开发布、审核和评论回复端到端验收。不要直接用于无人值守生产。

## 手动安装

需要 Python 3.12、Node.js >=18、可安全运行的 Chrome/Chromium（Windows 也可 Edge），以及有合法使用权的中文字体。使用自己信任的软件来源安装；本仓库不含这些二进制。

在仓库根目录，Linux/POSIX：

```sh
python3 -m venv runtime/.venv
runtime/.venv/bin/python -m pip install -r runtime/requirements.txt
(cd runtime/vendor/douyin-skills-09e9ccb6c484c59d69e11dbb4bc975c47e5510e5 && npm ci --ignore-scripts --no-audit --no-fund)
./runtime/douyin-agent version
./runtime/douyin-agent doctor
./runtime/douyin-agent policy
```

Windows PowerShell（依赖同上；下列步骤尚未在本次候选版本实测）：

```powershell
py -3.12 -m venv runtime/.venv
& runtime/.venv/Scripts/python.exe -m pip install -r runtime/requirements.txt
Push-Location runtime/vendor/douyin-skills-09e9ccb6c484c59d69e11dbb4bc975c47e5510e5
npm ci --ignore-scripts --no-audit --no-fund
Pop-Location
& runtime/douyin-agent.cmd doctor
```

`CHROME_BIN` 可显式指定浏览器；`DOUYIN_FONT` 可指定中文字体。不要添加 `--no-sandbox` 或规避自动化检测的参数。缺少操作系统权限时请换用合法支持浏览器沙箱的环境，而不是绕过限制。

项目 skill 位于 `.agents/skills/douyin-assistant/SKILL.md`。运行目录绑定相对于 skill 目录，不包含开发者路径；Agent 是否自动发现 skill 取决于宿主。移动或独立安装 skill 时须更新本机 `runtime.json`。

默认读 `runtime/policy.example.json`，发布和回复均禁用。只有取得当前用户明确授权后，才复制为 `runtime/policy.json` 并填写授权范围；不提交该文件。登录、验证码和平台验证由用户处理；未配置授权时不能发布或回复。未调用浏览器的 `doctor` 也可能报告缺少依赖/浏览器。

## 离线测试

```sh
runtime/.venv/bin/python -m unittest discover -s tests -v
```

Windows 使用 `.venv/Scripts/python.exe`。测试不登录、不发布、不下载依赖。渲染需 Pillow、FFmpeg 与中文字体；`references/commands.md` 中有分镜格式。

详见 [安全与隐私](SECURITY.md)、[变更记录](CHANGELOG.md)、[许可与来源](THIRD_PARTY.md) 和 skill 中的命令/验证说明。
