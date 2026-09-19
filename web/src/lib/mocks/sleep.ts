// 6장 목 규칙: 로딩 UI를 확인할 수 있도록 500~1500ms 지연을 흉내낸다.
export function sleep(minMs = 500, maxMs = 1500): Promise<void> {
  const ms = minMs + Math.random() * (maxMs - minMs);
  return new Promise((resolve) => setTimeout(resolve, ms));
}
