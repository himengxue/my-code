// Browser-half smoke test: loads lib/client.js with a fake module loader and a
// stubbed React, then checks the slot registration and renders the page once.
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const bundle = 'C:/Users/33969/.dsh/profiles/dsh-douyin-assistant/lib/client.js'
let loaded
globalThis.window = { __ModuleLoader__: { load: (entry) => { loaded = entry } } }

await import(pathToFileURL(bundle).href)
console.log('bundle id =', loaded?.id, '| factory =', typeof loaded?.factory)

const React = {
  createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
  useCallback: (fn) => fn,
  useState: (initial) => [initial, () => {}],
  useSyncExternalStore: (_subscribe, getSnapshot) => getSnapshot(),
}

const value = {
  enabled: true,
  publishVideos: false,
  autoComment: true,
  maxRepliesPerRun: 3,
  headed: true,
}
const form = {
  getSnapshot: () => ({ status: 'ready', value, revision: 4, writable: true }),
  subscribe: () => () => {},
  set: async (key, next) => { value[key] = next; return true },
}

const registrations = []
const ctx = {
  configForms: {
    get: (ns) => { console.log('configForms.get ->', ns); return form },
    whileServed: (namespaces, register) => { register(new Set(namespaces)); return () => {} },
  },
  slots: {
    inject: (_name, cb) => cb(),
    register: (options, component) => {
      registrations.push({ options, component })
      return () => {}
    },
  },
  effect: (factory) => { factory(); return () => {} },
}

const exports = loaded.factory((specifier) => {
  if (specifier === 'react') return React
  throw new Error('unexpected require: ' + specifier)
})
console.log('exports =', Object.keys(exports).join(','), '| inject =', JSON.stringify(exports.inject))
exports.apply(ctx)

const reg = registrations[0]
console.log('slot =', reg?.options.name, '| id =', reg?.options.id, '| order =', reg?.options.order, '| label =', reg?.options.label())
const tree = reg.component({})
const rendered = JSON.stringify(tree, (_k, v) => (typeof v === 'function' ? '[fn]' : v))
console.log('page title in tree =', rendered.includes('抖音助手'))
console.log('fields in tree =', ['总开关', '允许发布视频', '允许自动回复评论', '每轮最多回复条数', '有头浏览器'].every((t) => rendered.includes(t)))
console.log('current value reflected =', rendered.includes('"value":3'))
