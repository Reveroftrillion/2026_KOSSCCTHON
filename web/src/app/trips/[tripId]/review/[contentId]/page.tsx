'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, X } from 'lucide-react';
import { listTripContents, patchContent } from '@/lib/api';
import { CATEGORY_LABEL, CATEGORY_LIST, TIME_SLOT_LABEL, TIME_SLOT_LIST } from '@/lib/constants';
import type { Category, Content, TimeSlot } from '@/lib/types';
import { EmptyState, ErrorState, LoadingSteps } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function ReviewContentPage() {
  const { tripId, contentId } = useParams<{ tripId: string; contentId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const {
    data: contents,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['tripContents', tripId],
    queryFn: () => listTripContents(tripId),
  });

  const content = contents?.find((c) => c.contentId === contentId);

  const [syncedContentId, setSyncedContentId] = useState<string | null>(null);
  const [placeName, setPlaceName] = useState('');
  const [category, setCategory] = useState<Category>('cafe');
  const [recommendedTime, setRecommendedTime] = useState<TimeSlot | undefined>();
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [savedSummary, setSavedSummary] = useState<{ category: string; tags: string[] } | null>(null);

  // 조회된 콘텐츠로 편집 폼 상태를 초기화한다 (렌더링 도중 바로 동기화 — LoadingSteps.tsx와 동일한 패턴).
  if (content && content.contentId !== syncedContentId) {
    setSyncedContentId(content.contentId);
    setPlaceName(content.place.name);
    setCategory(content.category);
    setRecommendedTime(content.recommendedTime);
    setTags(content.tags);
    setSavedSummary(null);
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (!content) throw new Error('content missing');
      return patchContent(content.contentId, {
        place: { ...content.place, name: placeName.trim() || content.place.name },
        category,
        tags,
        recommendedTime,
      });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<Content[]>(['tripContents', tripId], (prev) =>
        prev?.map((c) => (c.contentId === updated.contentId ? updated : c))
      );
      // 5-3 규칙("AI 분석 확인 +1")이 저장 시 반영한 카테고리·태그를 그대로 보여준다.
      setSavedSummary({ category: CATEGORY_LABEL[updated.category], tags: updated.tags });
    },
  });

  function addTag() {
    const value = tagInput.trim();
    if (value && !tags.includes(value)) setTags((prev) => [...prev, value]);
    setTagInput('');
  }
  function removeTag(tag: string) {
    setTags((prev) => prev.filter((t) => t !== tag));
  }

  if (isPending) {
    return (
      <LoadingSteps steps={['분석 결과 불러오는 중']} className="mx-auto w-full max-w-md flex-1" />
    );
  }
  if (isError) {
    return <ErrorState className="mx-auto mt-10 w-full max-w-md" onRetry={() => refetch()} />;
  }
  if (!content) {
    return (
      <EmptyState
        className="mx-auto mt-10 w-full max-w-md"
        title="콘텐츠를 찾을 수 없어요"
        description="삭제되었거나 잘못된 링크예요."
      />
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-lg font-semibold text-foreground">AI 분석 결과 확인</h1>
        <p className="text-sm text-muted-foreground">필요하면 내용을 수정한 뒤 저장하세요.</p>
      </div>

      {content.place.verified ? (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="size-4 shrink-0" />
          장소 실존 확인됨
        </div>
      ) : (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span>장소를 실존 확인하지 못했어요. 아래 장소명을 정확히 수정해 주세요.</span>
        </div>
      )}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 rounded-xl border border-border bg-card p-4 text-sm shadow-sm">
        <div>
          <dt className="text-muted-foreground">주소</dt>
          <dd className="text-foreground">{content.place.address ?? '-'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">지역</dt>
          <dd className="text-foreground">{content.area}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">활동 유형</dt>
          <dd className="text-foreground">{content.activityType ?? '-'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">분위기</dt>
          <dd className="text-foreground">{content.mood ?? '-'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">신뢰도</dt>
          <dd className="text-foreground">{Math.round(content.confidence * 100)}%</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">영업 시간</dt>
          <dd className="text-foreground">{content.place.openHours ?? '-'}</dd>
        </div>
      </dl>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="flex flex-col gap-5"
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="placeName">장소명</Label>
          <Input
            id="placeName"
            value={placeName}
            onChange={(e) => setPlaceName(e.target.value)}
            placeholder="특정 장소가 있다면 입력해 주세요."
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>카테고리</Label>
          <Select value={category} onValueChange={(value) => setCategory(value as Category)}>
            <SelectTrigger className="w-full">
              <SelectValue>{(value: Category) => CATEGORY_LABEL[value]}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {CATEGORY_LIST.map((c) => (
                <SelectItem key={c} value={c}>
                  {CATEGORY_LABEL[c]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>추천 시간대</Label>
          <Select
            value={recommendedTime ?? ''}
            onValueChange={(value) => setRecommendedTime((value || undefined) as TimeSlot | undefined)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="선택 안 함">
                {(value: TimeSlot | '') => (value ? TIME_SLOT_LABEL[value] : '선택 안 함')}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {TIME_SLOT_LIST.map((t) => (
                <SelectItem key={t} value={t}>
                  {TIME_SLOT_LABEL[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="tagInput">태그</Label>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="gap-1 pr-1">
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    aria-label={`${tag} 삭제`}
                    className="rounded-full p-0.5 hover:bg-foreground/10"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Input
              id="tagInput"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addTag();
                }
              }}
              placeholder="태그 입력 후 Enter"
            />
            <Button type="button" variant="outline" onClick={addTag}>
              추가
            </Button>
          </div>
        </div>

        {mutation.isError && (
          <ErrorState message="저장에 실패했어요. 다시 시도해 주세요." onRetry={() => mutation.reset()} />
        )}

        {savedSummary && (
          <div className="rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-foreground">
            취향 DB 반영: {savedSummary.category} +1
            {savedSummary.tags.length > 0 &&
              `, ${savedSummary.tags.map((t) => `${t} +1`).join(', ')}`}{' '}
            (AI 분석 확인)
          </div>
        )}

        <div className="flex gap-2">
          <Button type="submit" size="lg" className="flex-1" disabled={mutation.isPending}>
            {mutation.isPending ? '저장 중...' : '저장하기'}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="lg"
            onClick={() => router.push(`/trips/${tripId}/basket`)}
          >
            장바구니로
          </Button>
        </div>
      </form>
    </div>
  );
}
