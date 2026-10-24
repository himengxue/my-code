# 验证范围

2026-10-24，基于 `098372dfe7603259d5ab1d04ebf78fb8d845fd60` 的本地兼容性修复候选。证据来自 Windows 上的 skill/CLI，扫码和平台核验由用户承担；云网页会话不作为 CLI 登录证据。

| 项目 | 结果 | 实际证据与边界 |
|---|---|---|
| 精确源码与许可 | passed | 原提交保留，MIT/上游署名不变；原 57 项源码哈希按 Git 的 LF 文本核对 |
| 原提交 Windows 全套测试 | failed | 15 项中 UID 测试因 Windows 没有 `os.geteuid` 出错；原结果保留 |
| 修复后离线回归 | passed | 37 unittest；含同一 key 去重、不确定提交禁止重发、默认无授权、路径/回复/DSH 绑定 |
| Windows 安装与启动 | passed | 独立 venv、官方依赖、既有 Python/Node/Edge；version/doctor 通过 |
| 独立 profile | passed | 实际 profile 在获准测试目录，loopback CDP；未读取或复制日常 Cookie |
| 扫码与本人账号核对 | passed | 用户扫码后 CLI `logged_in=true`，本人页及上传页核对授权账号 |
| 原创文字动画 | passed | CLI render 13 秒、720×1280、25 fps、无声 H.264，完整解码及关键画面检查 |
| 上传/封面/标题/文案 | passed | 一次 prepare；文件指纹、表单正文、竖版封面和自动横版裁剪可见 |
| AI 声明/公开可见 | passed | CLI 页面操作设置，发布前检查，公开视频仍显示 AI 声明 |
| 最终视频提交 | passed | 仅一次 publish；2026-10-24 11:01:10.767 UTC 返回发布成功/已提交 |
| 已发布状态/公开详情 | passed | 管理页 11:03:22.522 UTC 显示已发布；11:04:49.251 UTC 读取公开详情 |
| 本人作品检查 | passed | 当前 DIV 卡片与明确的本人作品容器交叉匹配；不使用推荐链接 |
| 新片评论 | passed | 读取返回 0；页面显示暂无评论，不伪造互动 |
| 旧作品真实评论读取 | passed | 读取一条真实贴纸评论；图像含义由截图检查，文本解析本身不识别贴纸内容 |
| 定向回复准备 | passed | 修复后只填入选定评论的内联回复框，顶层评论框保持空 |
| 真实定向回复发送 | blocked | 一次点击后出现短信身份核验；未完成核验，刷新后未找到回复；不重发 |
| 旧回复成功检测 | failed | 历史 CLI 错报 confirmed，截图显示核验弹窗及未发送草稿；原证据保留并纠正 |
| 回复安全修复的 DOM 检查 | passed | 12 项 about:blank 检查，含错误目标拒绝、定向输入/发送、隐藏/禁用草稿与无关预览排除及 SMS 停止；无平台评论副作用 |
| 修复后的真实回复持久成功 | not tested | 未完成用户核验，不再次点击；当前页回显保持 uncertain，需真实回执/独立重读 |
| DSH 版本/发现组件 | passed | 本机 0.2.0-rc.2；真实 Cordis Context + Registry/FileSystem 的 14 项离线 host-loader 检查通过，含自身及全部上级无 `.git` 的解压包 |
| DSH 完整模型会话/沙箱浏览器 | not tested | 未读模型凭证、未调用模型；Windows named-pipe 限制只是待测条件 |
| Linux 实际浏览器 | blocked | 既有云环境 socket/bwrap 启动约束未解决，未关闭 sandbox；本补丁仅做 Linux 启动参数模拟回归 |
| macOS、Windows 其他版本 | not tested | 不从单台 Windows 11 结果泛化 |

公开测试作品：[13 秒原创功能验证短片](https://www.douyin.com/video/7700187718818532617)。测试只提交这一条；其他作品没有被本任务编辑、删除或再发布。审核中与已公开分别报告。

原始截图、日志、数据库、账号信息和素材留在用户授权的本地目录，不随源码发布。完整环境、修复范围与历史审计见包根 `RELEASE_AUDIT.md`；DSH 组件测试不能代替模型会话验收。离线去重测试没有通过真实重复发片实施。
