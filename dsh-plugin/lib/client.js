// dsh-douyin-assistant — browser half.
//
// Adds one page to the Settings navigation (the leftmost list, next to 通用设置 /
// 模型 / 皮肤管理) that edits this plugin's own Config through `ctx.configForms`.
//
// Bundle shape: the client module system only registers a lazy-CJS factory here;
// the body runs when the page first materializes. `require` resolves against the
// shell's frozen module table, so `react` is the shell's own React instance and
// nothing is bundled.
window.__ModuleLoader__.load({
  id: 'dsh-douyin-assistant',
  factory: (require) => {
    const module = { exports: {} }
    const exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })

    const React = require('react')
    const h = React.createElement

    const NAMESPACE = 'douyin-assistant'

    /** Field metadata mirrors the Host `Config` schema; the Host validates every write. */
    const FIELDS = [
      {
        key: 'enabled',
        title: '总开关',
        hint: '关闭后除只读状态外的 douyin_* 工具都拒绝执行：不打开浏览器、不发布、不回复。',
        kind: 'boolean',
      },
      {
        key: 'publishVideos',
        title: '允许发布视频',
        hint: 'douyin_video 的 prepare / publish。关闭后只能查看作品列表。',
        kind: 'boolean',
      },
      {
        key: 'autoComment',
        title: '允许自动回复评论',
        hint: 'douyin_comment 的 prepare / send；读取评论列表不受影响。',
        kind: 'boolean',
      },
      {
        key: 'maxRepliesPerRun',
        title: '每轮最多回复条数',
        hint: '本次运行发送满该数量后拒绝继续发送；0 表示只准备不发送。',
        kind: 'number',
        min: 0,
        max: 5,
      },
      {
        key: 'headed',
        title: '有头浏览器',
        hint: '需要新开浏览器时使用有头模式，减少风控验证页；已有浏览器时自动附着。',
        kind: 'boolean',
      },
    ]

    const styles = {
      page: { display: 'flex', flexDirection: 'column', gap: '8px', padding: '4px 2px 24px' },
      title: { fontSize: '22px', fontWeight: 700, margin: '0 0 4px' },
      intro: { margin: '0 0 12px', opacity: 0.72, lineHeight: 1.6, fontSize: '13px' },
      card: {
        border: '1px solid rgba(127,127,127,0.28)',
        borderRadius: '12px',
        padding: '4px 16px',
        background: 'rgba(127,127,127,0.06)',
      },
      row: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
        padding: '14px 0',
        borderBottom: '1px solid rgba(127,127,127,0.18)',
      },
      rowLast: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px', padding: '14px 0' },
      label: { display: 'flex', flexDirection: 'column', gap: '4px', minWidth: 0 },
      labelText: { fontSize: '14px', fontWeight: 600 },
      hint: { fontSize: '12px', opacity: 0.66, lineHeight: 1.5 },
      switch: { width: '20px', height: '20px', accentColor: '#4c8bf5', cursor: 'pointer' },
      number: {
        width: '72px',
        padding: '6px 8px',
        borderRadius: '8px',
        border: '1px solid rgba(127,127,127,0.4)',
        background: 'transparent',
        color: 'inherit',
        fontSize: '14px',
      },
      notice: { minHeight: '20px', fontSize: '12px', opacity: 0.7, marginTop: '10px' },
      error: { color: '#d9534f' },
    }

    /**
     * One settings page bound to the plugin's Host namespace.
     * @param form - `ctx.configForms.get(NAMESPACE)`; its mirror is the only read path.
     * @returns the page component.
     */
    function createPage(form) {
      return function DouyinSettingsPage() {
        const subscribe = React.useCallback((listener) => form.subscribe(listener), [])
        const read = React.useCallback(() => form.getSnapshot(), [])
        const snapshot = React.useSyncExternalStore(subscribe, read)
        const [notice, setNotice] = React.useState(undefined)
        const [failure, setFailure] = React.useState(false)

        const status = snapshot?.status
        const value = snapshot?.value ?? {}

        const write = React.useCallback(
          async (key, next) => {
            setFailure(false)
            setNotice('保存中…')
            let ok = false
            try {
              ok = await form.set(key, next)
            } catch (error) {
              ok = false
            }
            setFailure(!ok)
            setNotice(ok ? '已保存，立即生效' : '保存失败，请重试')
          },
          [],
        )

        const rows = FIELDS.map((field, index) => {
          const last = index === FIELDS.length - 1
          const current = value[field.key]
          const control =
            field.kind === 'number'
              ? h('input', {
                  type: 'number',
                  min: field.min,
                  max: field.max,
                  step: 1,
                  value: current ?? '',
                  disabled: status !== 'ready',
                  style: styles.number,
                  onChange: (event) => {
                    const parsed = Number(event.target.value)
                    const next = Number.isFinite(parsed) ? Math.max(field.min, Math.min(field.max, Math.round(parsed))) : 0
                    void write(field.key, next)
                  },
                })
              : h('input', {
                  type: 'checkbox',
                  checked: current !== false,
                  disabled: status !== 'ready',
                  style: styles.switch,
                  onChange: (event) => { void write(field.key, event.target.checked) },
                })
          return h(
            'div',
            { key: field.key, style: last ? styles.rowLast : styles.row },
            h(
              'div',
              { style: styles.label },
              h('span', { style: styles.labelText }, field.title),
              h('span', { style: styles.hint }, field.hint),
            ),
            control,
          )
        })

        return h(
          'div',
          { style: styles.page },
          h('h2', { style: styles.title }, '抖音助手'),
          h(
            'p',
            { style: styles.intro },
            '把 douyin-assistant 的技能与本地执行器接进 DSH。这里的开关只会收窄执行器的权限：关掉某项后，对应工具会直接拒绝执行；打开也不会绕过执行器 policy.json 的授权和 dispatched/confirmed 账本。',
          ),
          h('div', { style: styles.card }, status === 'ready' ? rows : h('div', { style: styles.notice }, '正在读取配置…')),
          h(
            'div',
            { style: { ...styles.notice, ...(failure ? styles.error : {}) } },
            notice ?? '修改后立即保存，无需重启插件',
          ),
        )
      }
    }

    /** Client plugin identity. */
    const name = 'douyin-assistant-settings'
    /** `slots` renders the page; `configForms` owns reads and writes. */
    const inject = ['slots', 'configForms']

    /**
     * Register the page while the Host actually serves this namespace.
     * @param ctx - browser plugin context.
     */
    function apply(ctx) {
      const form = ctx.configForms.get(NAMESPACE)
      const Page = createPage(form)
      ctx.effect(() =>
        ctx.configForms.whileServed([NAMESPACE], () =>
          ctx.slots.inject('settings.section', () =>
            ctx.slots.register(
              {
                name: 'settings.section',
                id: NAMESPACE,
                order: 60,
                label: () => '抖音助手',
              },
              Page,
            ),
          ),
        ),
      )
    }

    exports.name = name
    exports.inject = inject
    exports.apply = apply
    return module.exports
  },
})
