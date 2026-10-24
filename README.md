# my-code

## Projects

- [抖音自主创作者 Skill / Runtime](douyin-assistant/README.md) — MIT source candidate; one Windows CLI publication verified, comment sending blocked by SMS verification. Includes a shared [DSH discovery entry](.agents/skills/douyin-assistant/SKILL.md); full DSH model-session/browser validation remains untested.
- [DSH 插件 `dsh-douyin-assistant`](dsh-plugin/README.md) — packages the skill above as a DeepSeek Harness plugin: one runtime skill, six `douyin_*` tools, and a Settings page. Executor policy, dedupe keys and the dispatched/confirmed ledger stay in the executor; the plugin adds gating only in the narrower direction.
