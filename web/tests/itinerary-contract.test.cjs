// No extra runner dependency or subprocess: node tests/itinerary-contract.test.cjs
const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')

function load(file, dependencies = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../src/lib/api', file), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', code)((name) => {
    if (!(name in dependencies)) throw new Error(`Unexpected import: ${name}`)
    return dependencies[name]
  }, module, module.exports)
  return module.exports
}

const adapter = load('itinerary-adapter.ts')
const trip = { tripId: 'trip-uuid', destination: '성수', startDate: '2026-09-20', endDate: '2026-09-22',
  dayStartTime: '13:00', dayEndTime: '20:00', members: [{ userId: 'user-uuid', name: '민수' }] }
const request = { date: '2026-09-21', area: '성수', startTime: '13:00', endTime: '20:00', includeMeals: false, mustVisitContentIds: [] }
const raw = { itinerary_id: 'itinerary-uuid', trip_id: trip.tripId, date: '2026-09-21', day_number: 2,
  time_range: '13:00 ~ 20:00', place_source: 'kakao', summary: '일정',
  schedule: [{ time: '13:00', place_id: 'place-uuid', place: '카페', category: 'cafe', reason: '추천 이유',
    related_users: ['user-uuid'], user_scores: { 'user-uuid': .4 }, group_score: .4,
    latitude: '37.5', longitude: '127.1', address: '서울 성동구' }],
  preference_coverage: { 'user-uuid': .4 },
  preference_reflection: { 'user-uuid': { matched_categories: ['cafe'], total_categories: 2, preference_reflection_percent: 50 } } }

test('request matches Backend date/user_conditions schema and uses trip bounds', () => {
  assert.deepEqual(adapter.toBackendRequest(request, trip), { date: request.date, user_conditions: [] })
  assert.throws(() => adapter.toBackendRequest({ ...request, date: '2026-09-30' }, trip))
  assert.throws(() => adapter.toBackendRequest({ ...request, startTime: '12:00' }, trip))
  assert.throws(() => adapter.toBackendRequest({ ...request, mustVisitContentIds: ['content-id'] }, trip))
})

test('response preserves IDs, reason, scores, reflection and map fields', () => {
  const result = adapter.fromBackendItinerary(raw, trip)
  const stop = result.days[0].items[0]
  assert.equal(result.itineraryId, raw.itinerary_id)
  assert.equal(result.tripId, raw.trip_id)
  assert.equal(result.days[0].day, 2)
  assert.equal(result.days[0].date, raw.date)
  assert.equal(stop.placeId, raw.schedule[0].place_id)
  assert.equal(stop.reason, raw.schedule[0].reason)
  assert.deepEqual(stop.userScores, raw.schedule[0].user_scores)
  assert.equal(stop.groupScore, .4)
  assert.equal(stop.relatedUsers[0].userId, 'user-uuid')
  assert.equal(stop.place.lat, 37.5)
  assert.equal(stop.place.lng, 127.1)
  assert.equal(stop.place.name, raw.schedule[0].place)
  assert.equal(stop.category, raw.schedule[0].category)
  assert.equal(stop.startTime, raw.schedule[0].time)
  assert.equal(result.summary, raw.summary)
  assert.equal(result.placeSource, raw.place_source)
  assert.equal(stop.place.address, '서울 성동구')
  assert.equal(stop.endTime, '20:00')
  assert.equal(result.reflection[0].name, '민수')
  assert.equal(result.reflection[0].reflectionPercent, 50)
  assert.deepEqual(result.preferenceCoverage, raw.preference_coverage)
  assert.deepEqual(result.preferenceReflection, raw.preference_reflection)
})

test('missing coordinates and reflection are not fabricated as zero', () => {
  const input = structuredClone(raw)
  input.schedule[0].latitude = null
  input.schedule[0].longitude = 'invalid'
  input.preference_reflection['user-uuid'] = { matched_categories: [], total_categories: 0, preference_reflection_percent: null }
  const result = adapter.fromBackendItinerary(input, trip)
  assert.equal(result.days[0].items[0].place.lat, undefined)
  assert.equal(result.days[0].items[0].place.lng, undefined)
  assert.equal(result.reflection[0].reflectionPercent, null)
})

test('real response adapter rejects mock and legacy snapshots explicitly', () => {
  assert.throws(() => adapter.fromBackendItinerary({ ...raw, place_source: 'mock' }, trip), /샘플/)
  assert.throws(() => adapter.fromBackendItinerary({ itinerary_id: 'old', legacy: true }, trip), /이전 형식/)
})

function api(http) {
  return load('itinerary.ts', { './http': { http, USE_MOCK: false }, './trips': { getTrip: async () => trip },
    './itinerary-adapter': adapter, '@/lib/mocks': new Proxy({}, { get() { throw new Error('Mock accessed in real mode') } }) })
}

test('real POST uses /api/trips/.../itinerary and adapted request', async () => {
  const service = api(async (url, init) => {
    assert.equal(url, '/api/trips/trip-uuid/itinerary')
    assert.equal(init.method, 'POST')
    assert.deepEqual(JSON.parse(init.body), { date: request.date, user_conditions: [] })
    return raw
  })
  assert.equal((await service.postGroupItinerary(trip.tripId, request)).itineraryId, raw.itinerary_id)
})

test('real GET loads list then actual itinerary detail', async () => {
  const urls = []
  const service = api(async url => { urls.push(url); return urls.length === 1 ? [raw] : raw })
  assert.equal((await service.getTripItinerary(trip.tripId)).itineraryId, raw.itinerary_id)
  assert.deepEqual(urls, ['/api/trips/trip-uuid/itineraries', '/api/trips/trip-uuid/itineraries/itinerary-uuid'])
})

test('empty list is null; server errors propagate without mock fallback', async () => {
  assert.equal(await api(async () => []).getTripItinerary(trip.tripId), null)
  await assert.rejects(api(async () => { throw new Error('provider error') }).getTripItinerary(trip.tripId), /provider error/)
})

test('trip adapter pads MySQL single-digit hour for HTML time input', async () => {
  const service = load('trips.ts', { './http': { USE_MOCK: false, http: async url => url.endsWith('/members')
    ? { data: [] }
    : { data: { trip_id: trip.tripId, trip_name: '여행', region: '성수', start_date: trip.startDate,
      end_date: trip.endDate, day_start_time: '9:00:00', day_end_time: '20:00:00' } } }, '@/lib/mocks': {} })
  const result = await service.getTrip(trip.tripId)
  assert.equal(result.dayStartTime, '09:00')
  assert.equal(result.dayEndTime, '20:00')
})

test('multi-day reload selects final travel day without mixing day-one fields', async () => {
  const dayOne = { ...structuredClone(raw), itinerary_id: 'day-one', date: trip.startDate, day_number: 1 }
  const dayTwo = { ...structuredClone(raw), itinerary_id: 'day-two' }
  const urls = []
  const service = api(async url => {
    urls.push(url)
    return urls.length === 1 ? [dayOne, dayTwo] : dayTwo
  })
  const result = await service.getTripItinerary(trip.tripId)
  assert.equal(urls[1], '/api/trips/trip-uuid/itineraries/day-two')
  assert.equal(result.itineraryId, 'day-two')
  assert.equal(result.days.length, 1)
  assert.equal(result.days[0].day, 2)
  assert.equal(result.days[0].date, dayTwo.date)
  assert.equal(adapter.toBackendRequest({ ...request, date: trip.startDate }, trip).date, trip.startDate)
})

test('mixed populated and empty profiles retain null reflection and valid scores', () => {
  const input = structuredClone(raw)
  input.preference_coverage['empty-user'] = 0
  input.preference_reflection['empty-user'] = { matched_categories: [], total_categories: 0, preference_reflection_percent: null }
  input.schedule[0].user_scores['empty-user'] = 0
  const result = adapter.fromBackendItinerary(input, { ...trip, members: [...trip.members, { userId: 'empty-user', name: '새 멤버' }] })
  assert.deepEqual(result.reflection.find(member => member.userId === 'empty-user'), {
    userId: 'empty-user', name: '새 멤버', reflectionPercent: null, coveredTop: 0, totalTop: 0,
  })
  assert.equal(result.reflection[0].reflectionPercent, 50)
  assert.equal(result.allMembersCovered, false)
  assert.equal(result.days[0].items[0].userScores['empty-user'], 0)
  assert.ok(!JSON.stringify(result).includes('NaN'))
})
