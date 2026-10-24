# 命令与制作格式

先读取技能目录的 `runtime.json`。以下用 `douyin-agent` 表示其中 `home` 目录下 Linux 的 `douyin-agent`（Windows 为 `douyin-agent.cmd`），不是要求另装 PyPI 同名包。参数文本存 UTF-8 文件，路径含空格时加引号。

| 命令 | 实际作用 |
|---|---|
| `doctor` / `version` | 不打开浏览器的环境和版本检查 |
| `policy` / `brief` / `jobs` | 运营范围、历史主题及任务状态 |
| `--headed auth login` | 打开独立浏览器，取得抖音登录二维码 |
| `auth status` / `auth wait` | 当前登录状态/等待扫码 |
| `search "关键词" --limit 5` / `trending` | 当前浏览器的抖音搜索/热点 |
| `topic --file topic.json` | 保存 AI 自行设计的主题 |
| `render --storyboard storyboard.json --out 新目录` | 本地生成原创无声文字动画、封面和发布清单 |
| `video mine --limit 20` | 从本人创作者中心记录当前已加载作品 |
| `video prepare --manifest publish.json` | 上传并填写视频、封面、标题与简介，返回任务 ID |
| `video publish --job ID` | 核对素材和网页设置后实际点击发布，并保存提交结果 |
| `comment list --video 视频ID --limit 20` | 获取可见评论与用于精确定位的 key |
| `comment prepare --key KEY --text-file reply.txt` | 定位原评论、进入定向回复模式并填写回复 |
| `comment send --job ID` | 实际发送该回复，并检查对应线程中的新增内容 |
| `browser snapshot --target TARGET_ID` | 读取当前页面与可操作节点 |
| `browser screenshot --target TARGET_ID` | 保存当前页面 PNG，便于核对二维码或发布设置 |
| `browser click --target TARGET_ID --node NODE_ID` | 点击当前观察中的普通控件，例如 AI 声明和确定 |
| `browser fill --target TARGET_ID --node NODE_ID --text-file text.txt` | 填写空输入框或核对同文，不覆盖已有不同草稿 |
| `browser open --url 抖音官方URL` | 打开实际已知的抖音页面 |

`video prepare` 和发布设置的等待可能需要几十秒。运行中的命令有进程句柄时继续等待，不重复启动上传。最终写操作记录在 `data/operator.sqlite`；同一作品和同一评论有去重键，两个 Agent 共用浏览器操作锁。

## 自主选题记录

`topic.json` 可以包含 `title`、`audience`、`angle`、`why_now`、`sources`、`difference_from_recent_posts`。写作由当前 AI 完成，执行器不额外调用模型、不要求另填 DeepSeek/OpenAI API Key。

## 内置视频分镜

```json
{
  "topic": "如何让画面里的主体更清楚",
  "title": "拍之前，先看这三处",
  "series": "一分钟视觉实验",
  "caption": "用三个简单观察整理画面。AI原创演示 #摄影 #构图",
  "scenes": [
    {"headline": "先确定你想让人看哪里", "body": "画面里如果每个角落都很抢眼，\n主体反而容易被淹没。", "duration": 7},
    {"headline": "检查主体后方", "body": "换一个站位，\n让背景里的强线条避开主体。", "duration": 7},
    {"headline": "再决定留下什么", "body": "把画面边缘多余的干扰去掉，\n再拍一张作对比。", "duration": 7}
  ]
}
```

这是格式示例，不是固定选题库。`render` 输出 720×1280、25fps H.264 MP4、PNG 封面与 `publish.json`，默认无音轨。每场景 2–30 秒，文字过长会拒绝。更丰富的视频可用其他实际可用工具生成，仍使用下面的发布清单。

## 发布清单

```json
{
  "topic": "本次实际主题",
  "title": "实际标题",
  "video": "video.mp4",
  "cover": "cover.png",
  "caption_file": "caption.txt",
  "ai_generated": true,
  "visibility": "public"
}
```

相对路径基于清单所在目录。源文件生成指纹后发生变化，执行器会停止该发布任务，需重新准备。当前专用发布流程处理 AI 原创公开视频；定时、私密和非 AI 稿件不在该自动提交器的默认实现范围。

## 首次其他电脑的授权

分享包的 `policy.example.json` 不包含原用户授权。新主人明确选择自主运营后，Agent 将本机 `policy.json` 的 `mode` 设为 `autonomous_creator`，打开 `publish_videos` 与 `reply_to_own_video_comments`，在 `authorization` 写入该用户本次授权的日期和范围。不要直接搬用其他用户的授权内容。
