// Run with node tests/reflection-panel.test.cjs; render the actual component offline.
const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')
const source = fs.readFileSync(path.join(__dirname, '../src/components/fe2/ReflectionPanel.tsx'), 'utf8')
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
const loaded = { exports: {} }
new Function('require', 'module', 'exports', code)(name => {
  if (name === 'react/jsx-runtime') return require(name)
  if (name === '@/lib/utils') return { cn: (...values) => values.filter(Boolean).join(' ') }
  if (name === './MemberAvatar') return { default: () => null }
  throw new Error(`Unexpected dependency: ${name}`)
}, loaded, loaded.exports)

const reflected = { userId: 'a', name: 'A', totalTop: 1, coveredTop: 1, reflectionPercent: 100 }
function render(members, allMembersCovered = false) {
  return renderToStaticMarkup(React.createElement(loaded.exports.default, {
    itinerary: { reflection: members, allMembersCovered, rebalanced: false },
  }))
}

test('null reflection is excluded and mixed-member heading uses requested wording', () => {
  const html = render([reflected, { ...reflected, userId: 'b', reflectionPercent: null }])
  assert.match(html, /분석 가능한 멤버 취향 모두 반영/)
  assert.match(html, /일부 멤버는 아직 취향 데이터가 없어요\./)
  assert.match(html, /취향 데이터 없음/)
  assert.doesNotMatch(html, /미반영 멤버 있음|일정에 취향이 한 번도|role="alert"|NaN|undefined/)
})

test('zero total categories is excluded even when reflection is numeric zero', () => {
  const html = render([reflected, { ...reflected, userId: 'b', totalTop: 0, coveredTop: 0, reflectionPercent: 0 }])
  assert.match(html, /분석 가능한 멤버 취향 모두 반영/)
  assert.match(html, /취향 데이터 없음/)
  assert.doesNotMatch(html, /미반영 멤버 있음|role="alert"/)
})

test('zero reflection with categories is unreflected regardless of coverage flag', () => {
  const html = render([reflected, { ...reflected, userId: 'b', coveredTop: 0, reflectionPercent: 0 },
    { ...reflected, userId: 'c', totalTop: 0, reflectionPercent: null }], true)
  assert.match(html, /미반영 멤버 있음/)
  assert.match(html, /일정에 취향이 한 번도 반영되지 않은 멤버가 있어요\./)
  assert.match(html, /role="alert"/)
})

test('all evaluable reflected members keep original heading', () => {
  const html = render([reflected, { ...reflected, userId: 'b', reflectionPercent: 50 }])
  assert.match(html, /모든 멤버 반영/)
  assert.doesNotMatch(html, /일부 멤버|미반영 멤버/)
})

test('all members without preferences are not described as reflected or unreflected', () => {
  const html = render([{ ...reflected, totalTop: 0, coveredTop: 0, reflectionPercent: null }])
  assert.match(html, /아직 평가할 취향 데이터가 없어요\./)
  assert.doesNotMatch(html, /모든 멤버 반영|미반영 멤버|role="progressbar"|NaN|undefined/)
})
