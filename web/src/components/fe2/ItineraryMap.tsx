'use client'

import { CustomOverlayMap, Map, Polyline, useKakaoLoader } from 'react-kakao-maps-sdk'
import { cn } from '@/lib/utils'
import type { ItineraryItem } from '@/lib/types'

const KAKAO_MAP_KEY = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY

interface Point {
  order: number
  name: string
  lat: number
  lng: number
}

function toPoints(items: ItineraryItem[]): Point[] {
  return items
    .filter((item) => item.place.lat != null && item.place.lng != null)
    .map((item) => ({ order: item.order, name: item.place.name, lat: item.place.lat as number, lng: item.place.lng as number }))
}

// 키가 없을 때 보여줄 비활성 상태. SPEC 8장 F2-08 완료 기준: "키 없으면 지도만 비활성".
function MapDisabled({ reason }: { reason: string }) {
  return (
    <div className="flex h-56 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-sm text-muted-foreground">
      {reason}
    </div>
  )
}

function KakaoItineraryMap({
  items,
  selectedOrder,
  onSelect,
}: {
  items: ItineraryItem[]
  selectedOrder: number | null
  onSelect: (order: number) => void
}) {
  const [loading, error] = useKakaoLoader({ appkey: KAKAO_MAP_KEY as string })
  const points = toPoints(items)

  if (loading) return <MapDisabled reason="지도를 불러오는 중…" />
  if (error) return <MapDisabled reason="지도를 불러오지 못했어요. 목록으로 확인해 주세요." />
  if (points.length === 0) return <MapDisabled reason="지도에 표시할 좌표가 있는 장소가 없어요." />

  const selected = points.find((p) => p.order === selectedOrder)
  const center = selected ?? points[0]

  return (
    <Map
      center={center}
      level={5}
      isPanto
      className="h-56 w-full overflow-hidden rounded-xl border border-slate-200"
    >
      <Polyline
        path={points.map((p) => ({ lat: p.lat, lng: p.lng }))}
        strokeColor="#0d9488"
        strokeWeight={3}
        strokeOpacity={0.7}
      />
      {points.map((p) => {
        const active = p.order === selectedOrder
        return (
          <CustomOverlayMap key={p.order} position={{ lat: p.lat, lng: p.lng }} yAnchor={1} clickable>
            <button
              type="button"
              onClick={() => onSelect(p.order)}
              title={p.name}
              className={cn(
                'flex h-7 w-7 items-center justify-center rounded-full border-2 border-white text-xs font-bold text-white shadow',
                active ? 'bg-blue-700 ring-2 ring-blue-300' : 'bg-blue-500',
              )}
            >
              {p.order}
            </button>
          </CustomOverlayMap>
        )
      })}
    </Map>
  )
}

// 카카오 지도 키(NEXT_PUBLIC_KAKAO_MAP_KEY)가 없으면 지도 없이도 나머지 화면은 그대로 동작해야 한다.
export default function ItineraryMap({
  items,
  selectedOrder,
  onSelect,
}: {
  items: ItineraryItem[]
  selectedOrder: number | null
  onSelect: (order: number) => void
}) {
  if (!KAKAO_MAP_KEY) {
    return <MapDisabled reason="카카오 지도 키가 설정되지 않아 지도를 표시할 수 없어요. 아래 목록으로 확인해 주세요." />
  }
  return <KakaoItineraryMap items={items} selectedOrder={selectedOrder} onSelect={onSelect} />
}
