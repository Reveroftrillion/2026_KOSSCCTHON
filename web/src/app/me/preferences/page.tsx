'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { getUserPreferences } from '@/lib/api';
import { useUser } from '@/lib/user-context';
import { EmptyState, ErrorState, LoadingSteps, PreferenceBar } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';

export default function MyPreferencesPage() {
  const { currentUser } = useUser();

  const {
    data,
    isPending,
    isError,
    refetch,
    isFetching,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ['userPreferences', currentUser.userId],
    queryFn: () => getUserPreferences(currentUser.userId),
  });

  // 유저 전환/재조회 시점을 감지해 직전 대비 상승한 항목만 하이라이트한다
  // (LoadingSteps.tsx와 같은 "렌더링 중 동기화" 패턴 — effect로 setState하지 않는다).
  const [syncedUserId, setSyncedUserId] = useState<string | null>(null);
  const [prevNormalized, setPrevNormalized] = useState<Record<string, number>>({});
  const [highlightKeys, setHighlightKeys] = useState<Set<string>>(new Set());
  const [seenAt, setSeenAt] = useState<number | null>(null);

  if (currentUser.userId !== syncedUserId) {
    setSyncedUserId(currentUser.userId);
    setPrevNormalized({});
    setHighlightKeys(new Set());
    setSeenAt(null);
  } else if (data && dataUpdatedAt !== seenAt) {
    const risen = new Set<string>();
    for (const item of data.all) {
      if (item.normalized > (prevNormalized[item.key] ?? 0)) risen.add(item.key);
    }
    setHighlightKeys(seenAt === null ? new Set() : risen);
    setPrevNormalized(Object.fromEntries(data.all.map((item) => [item.key, item.normalized])));
    setSeenAt(dataUpdatedAt);
  }

  if (isPending) {
    return <LoadingSteps steps={['취향 프로필 불러오는 중']} className="mx-auto w-full max-w-md flex-1" />;
  }
  if (isError) {
    return <ErrorState className="mx-auto mt-10 w-full max-w-md" onRetry={() => refetch()} />;
  }

  const categories = data.all.filter((item) => item.type === 'category').sort((a, b) => b.normalized - a.normalized);
  const tags = data.all
    .filter((item) => item.type === 'tag')
    .sort((a, b) => b.normalized - a.normalized)
    .slice(0, 8);

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-4 py-8">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-foreground">{currentUser.name}님의 취향 프로필</h1>
          <p className="text-sm text-muted-foreground">상단에서 다른 멤버로 전환할 수 있어요.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? '새로고침 중...' : '새로고침'}
        </Button>
      </div>

      {data.all.length === 0 ? (
        <EmptyState
          title="아직 취향 데이터가 없어요"
          description="숏폼을 저장하면 카테고리·태그 취향이 쌓여요."
          action={
            <Link href="/" className={buttonVariants()}>
              숏폼 담으러 가기
            </Link>
          }
        />
      ) : (
        <>
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">상위 카테고리</h2>
            <div className="flex flex-col gap-3 rounded-xl border border-border p-4">
              {categories.map((item) => (
                <PreferenceBar key={item.key} item={item} highlighted={highlightKeys.has(item.key)} />
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">상위 태그</h2>
            <div className="flex flex-wrap gap-2">
              {tags.map((item) => (
                <Badge
                  key={item.key}
                  variant={highlightKeys.has(item.key) ? 'default' : 'secondary'}
                  className="gap-1"
                >
                  {item.label} · 근거 {item.evidenceCount}건
                </Badge>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
