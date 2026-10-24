import { apply, name, inject, Config } from 'file:///C:/Users/33969/.dsh/profiles/dsh-douyin-assistant/lib/index.js'

const volatile = (value) => ({ get: () => value })
const config = {
  enabled: volatile(process.env.SMOKE_DISABLED === '1' ? false : true),
  publishVideos: volatile(process.env.SMOKE_NO_PUBLISH === '1' ? false : true),
  autoComment: volatile(process.env.SMOKE_NO_COMMENT === '1' ? false : true),
  maxRepliesPerRun: volatile(5),
  headed: volatile(false),
}

const tools = []
const skills = []
const ctx = {
  logger: console,
  on: () => () => {},
  tools: { register: (definition) => { tools.push(definition); return () => {} } },
  skills: { register: (skill) => { skills.push(skill); return () => {} } },
}

console.log('name =', name, '| inject =', JSON.stringify(inject))
console.log('Config schema =', typeof Config, '| has ~standard =', Boolean(Config?.['~standard']), '| dict keys =', Object.keys(Config?.dict ?? {}).join(','))
apply(ctx, config)

const status = tools.find((t) => t.name === 'douyin_status')
const video = tools.find((t) => t.name === 'douyin_video')
const comment = tools.find((t) => t.name === 'douyin_comment')

console.log('tools =', tools.map((t) => t.name).join(','))
console.log('skill =', skills[0]?.name, '| source', skills[0]?.source)

if (process.env.SMOKE_DISABLED === '1') {
  console.log('disabled > version:', JSON.stringify(await status.execute({ command: 'version' }, {})))
  console.log('disabled > browser:', JSON.stringify(await tools.find((t) => t.name === 'douyin_browser').execute({ action: 'snapshot', target: 'x' }, {})))
  console.log('disabled > policy (readonly):', JSON.stringify(await status.execute({ command: 'policy' }, {})).slice(0, 80))
} else if (process.env.SMOKE_NO_PUBLISH === '1') {
  console.log('no-publish > prepare:', JSON.stringify(await video.execute({ action: 'prepare', manifest: 'x' }, {})))
} else if (process.env.SMOKE_NO_COMMENT === '1') {
  console.log('no-comment > prepare:', JSON.stringify(await comment.execute({ action: 'prepare', key: 'k', text: 'hi' }, {})))
} else {
  console.log('version ->', JSON.stringify(await status.execute({ command: 'version' }, {})))
  console.log('policy mode ->', (await status.execute({ command: 'policy' }, {}))?.data?.mode)
  const mine = await video.execute({ action: 'mine', limit: 1 }, {})
  console.log('mine ok ->', mine?.ok)
}
