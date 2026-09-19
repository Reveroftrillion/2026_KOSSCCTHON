// Offline contracts: node tests/auth-contract.test.cjs
const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')

function load(file, dependencies = {}, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../src', file), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', 'window', 'fetch', 'process', code)(name => {
    if (!(name in dependencies)) throw new Error(`Unexpected dependency: ${name}`)
    return dependencies[name]
  }, module, module.exports, globals.window, globals.fetch, { env: globals.env ?? {} })
  return module.exports
}

function fixture(mock = false) {
  const data = new Map()
  const events = []
  const browser = { localStorage: { getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) },
    dispatchEvent: event => events.push(event.type) }
  const tokens = load('lib/auth-token.ts', {}, { window: browser })
  const requests = []
  let responder = () => new Response('{}')
  const http = load('lib/api/http.ts', { '../auth-token': tokens }, {
    window: browser, env: { NEXT_PUBLIC_USE_MOCK: String(mock) },
    fetch: async (url, init) => { requests.push({ url, init }); return responder(url, init) },
  })
  const auth = load('lib/api/auth.ts', { './http': http })
  return { tokens, data, events, requests, http, auth, respond: fn => { responder = fn } }
}

test('login maps token/user and does not send stored bearer to public endpoint', async () => {
  const f = fixture()
  f.tokens.setAccessToken('old-test-token')
  f.respond(() => Response.json({ access_token: 'new-test-token', token_type: 'bearer', user: { user_id: 'uuid', name: 'User', email: 'test@example.com' } }))
  assert.deepEqual(await f.auth.login({ email: 'test@example.com', password: 'test-password' }), {
    accessToken: 'new-test-token', user: { userId: 'uuid', name: 'User' },
  })
  assert.equal(f.requests[0].url, 'http://localhost:8000/api/auth/login')
  assert.equal(f.requests[0].init.headers.get('Authorization'), null)
})

test('signup maps existing create-user response without logging in', async () => {
  const f = fixture()
  f.respond(() => Response.json({ status: 'success', user_id: 'first-user', name: 'First', email: 'first@example.com' }, { status: 201 }))
  assert.deepEqual(await f.auth.signup({ name: 'First', email: 'first@example.com', password: 'test-password' }), { userId: 'first-user', name: 'First' })
  assert.equal(f.requests[0].url, 'http://localhost:8000/api/users')
  assert.equal(f.tokens.getAccessToken(), '')
})

test('real requests attach bearer; mock requests do not', async () => {
  for (const mock of [false, true]) {
    const f = fixture(mock)
    f.tokens.setAccessToken('test-token')
    await f.http.http('/api/users')
    assert.equal(f.requests[0].init.headers.get('Authorization'), mock ? null : 'Bearer test-token')
  }
})

test('invalid login error is surfaced without expiration redirect loop', async () => {
  const f = fixture()
  f.respond(() => Response.json({ detail: '이메일 또는 비밀번호가 올바르지 않습니다.' }, { status: 401 }))
  await assert.rejects(f.auth.login({ email: 'test@example.com', password: 'wrong' }), /이메일 또는 비밀번호/)
  assert.ok(!f.events.includes(f.tokens.AUTH_EXPIRED))
  assert.equal(f.requests.length, 1)
})

test('no token makes no identity request and ignores stored demo user ID', async () => {
  const f = fixture()
  f.data.set('tripclip:current-user-id', 'another-user')
  assert.equal(await f.auth.resolveCurrentUser(f.tokens.getAccessToken()), null)
  assert.equal(f.requests.length, 0)
})

test('current user comes only from /auth/me, never first /users entry', async () => {
  const f = fixture()
  f.data.set('tripclip:current-user-id', 'spoofed')
  f.tokens.setAccessToken('test-token')
  f.respond(() => Response.json({ user_id: 'authenticated', name: 'Real', email: 'real@example.com' }))
  assert.deepEqual(await f.auth.resolveCurrentUser(f.tokens.getAccessToken()), { userId: 'authenticated', name: 'Real' })
  assert.equal(f.requests[0].url, 'http://localhost:8000/api/auth/me')
  assert.equal(f.requests.length, 1)
})

test('401 clears current token and notifies redirect; late old 401 preserves new login', async () => {
  const f = fixture()
  f.tokens.setAccessToken('expired-test-token')
  f.respond(() => Response.json({ detail: '로그인이 필요합니다.' }, { status: 401 }))
  await assert.rejects(f.auth.getMe('expired-test-token'))
  assert.equal(f.tokens.getAccessToken(), '')
  assert.ok(f.events.includes(f.tokens.AUTH_EXPIRED))
  f.tokens.setAccessToken('new-test-token')
  await assert.rejects(f.auth.getMe('old-test-token'))
  assert.equal(f.tokens.getAccessToken(), 'new-test-token')
})

test('duplicate signup and validation detail are shown; connection failure is safe', async () => {
  const f = fixture()
  f.respond(() => Response.json({ detail: '이미 존재하는 이메일입니다.' }, { status: 400 }))
  await assert.rejects(f.auth.signup({}), /이미 존재하는 이메일/)
  f.respond(() => Response.json({ detail: [{ msg: 'Invalid email', input: 'not-echoed' }] }, { status: 422 }))
  await assert.rejects(f.auth.signup({}), /Invalid email/)
  f.respond(() => { throw new Error('internal') })
  await assert.rejects(f.auth.login({}), /서버에 연결할 수 없어요/)
})

test('public routes render on empty DB/no token; protected route does not render children', () => {
  for (const route of ['/', '/signup', '/login', '/trips/new', '/me/preferences']) {
    const queries = []
    const context = load('lib/user-context.tsx', {
      react: React, 'react/jsx-runtime': require('react/jsx-runtime'),
      '@tanstack/react-query': { useQuery: options => { queries.push(options); return { isPending: true } }, useQueryClient: () => ({ clear() {} }) },
      'next/navigation': { usePathname: () => route, useRouter: () => ({ replace() {} }) },
      '@/lib/api/http': { USE_MOCK: false }, '@/lib/api/users': { listUsers() { throw new Error('Public user listing') } },
      '@/lib/api/auth': { resolveCurrentUser: async () => null },
      '@/lib/auth-token': { subscribeAuth: () => () => {}, getAccessToken: () => '', AUTH_EXPIRED: 'expired' },
    })
    const html = renderToStaticMarkup(React.createElement(context.UserProvider, null, React.createElement('p', null, 'page-content')))
    assert.equal(html.includes('page-content'), ['/', '/signup', '/login'].includes(route))
    assert.ok(queries.every(query => !query.enabled))
    assert.ok(!html.includes('등록된 사용자가 없습니다'))
  }
})
