---
name: douyin-assistant
description: 抖音原创创作、本地渲染、独立浏览器登录、上传发布和本人作品普通评论处理的仓库入口；通过共用执行器工作，适用于可运行本地命令的 Codex 与 DeepSeek Harness。
---

# 整仓发现入口

本文件只负责 `my-code` 整仓的 skill 发现。开始任务前，必须读取并遵循唯一的 [完整技能](../../../douyin-assistant/.agents/skills/douyin-assistant/SKILL.md)，再按该文件同目录的 `runtime.json` 定位执行器。所有相对资源以完整技能目录为基准，不能以本入口目录为基准；不要建立第二份 runtime 或复制账号状态。

可从仓库根运行 `python douyin-assistant/tools/resolve_runtime.py` 检查路径。它只读取绑定并返回 JSON；`ok=false` 或非零退出码时停止，报告缺失文件。安装、平台要求与 DSH 验证范围见 [兼容说明](../../../douyin-assistant/DSH_COMPATIBILITY.md)。默认策略禁止发布和回复；登录/验证码由用户处理，遇风控停止，提交不确定先核对远端，不自动重发。
