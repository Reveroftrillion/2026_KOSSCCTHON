'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { getTrip, listTripContents } from '@/lib/api';
import { CATEGORY_LABEL, CATEGORY_LIST } from '@/lib/constants';
import type { Category, Content } from '@/lib/types';
import { EmptyState, ErrorState, LoadingSteps, UserAvatar } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { buttonVariants } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const ALL = 'all';

export default function BasketPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const [categoryFilter, setCategoryFilter] = useState<Category | typeof ALL>(ALL);
  const [memberFilter, setMemberFilter] = useState<string>(ALL);

  const tripQuery = useQuery({ queryKey: ['trip', tripId], queryFn: () => getTrip(tripId) });
  const contentsQuery = useQuery({
    queryKey: ['tripContents', tripId],
    queryFn: () => listTripContents(tripId),
  });

  const contents = contentsQuery.data ?? [];
  const members = tripQuery.data?.members ?? [];

  const memberById = new Map(members.map((m) => [m.userId, m]));

  const countsByMember = new Map<string, number>();
  for (const content of contents) {
    countsByMember.set(content.userId, (countsByMember.get(content.userId) ?? 0) + 1);
  }

  const filteredContents = contents.filter(
    (c) =>
      (categoryFilter === ALL || c.category === categoryFilter) &&
      (memberFilter === ALL || c.userId === memberFilter)
  );

  const isPending = tripQuery.isPending || contentsQuery.isPending;
  const isError = tripQuery.isError || contentsQuery.isError;

  if (isPending) {
    return <LoadingSteps steps={['장바구니 불러오는 중']} className="mx-auto w-full max-w-2xl flex-1" />;
  }
  if (isError) {
    return (
      <ErrorState
        className="mx-auto mt-10 w-full max-w-2xl"
        onRetry={() => {
          tripQuery.refetch();
          contentsQuery.refetch();
        }}
      />
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-lg font-semibold text-foreground">여행 장바구니</h1>
        <p className="text-sm text-muted-foreground">멤버들이 저장한 장소를 한눈에 확인해요.</p>
      </div>

      {members.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {members.map((member) => (
            <span key={member.userId} className="flex items-center gap-1.5 text-muted-foreground">
              <UserAvatar user={member} size="sm" />
              {member.name} {countsByMember.get(member.userId) ?? 0}개
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Select value={categoryFilter} onValueChange={(v) => setCategoryFilter(v as Category | typeof ALL)}>
          <SelectTrigger size="sm">
            <SelectValue>
              {(value: Category | typeof ALL) => (value === ALL ? '전체 카테고리' : CATEGORY_LABEL[value])}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 카테고리</SelectItem>
            {CATEGORY_LIST.map((c) => (
              <SelectItem key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={memberFilter} onValueChange={(v) => setMemberFilter(v ?? ALL)}>
          <SelectTrigger size="sm">
            <SelectValue>
              {(value: string) => (value === ALL ? '전체 멤버' : (memberById.get(value)?.name ?? value))}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 멤버</SelectItem>
            {members.map((member) => (
              <SelectItem key={member.userId} value={member.userId}>
                {member.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {contents.length === 0 ? (
        <EmptyState
          title="첫 숏폼을 담아보세요"
          description="릴스·쇼츠·틱톡 링크를 저장하면 여기에 쌓여요."
          action={
            <Link href={`/trips/${tripId}/add`} className={buttonVariants()}>
              숏폼 담으러 가기
            </Link>
          }
        />
      ) : filteredContents.length === 0 ? (
        <EmptyState title="조건에 맞는 장소가 없어요" description="필터를 바꿔서 다시 찾아보세요." />
      ) : (
        <ul className="flex flex-col gap-3">
          {filteredContents.map((content) => (
            <ContentCard key={content.contentId} content={content} saver={memberById.get(content.userId)} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ContentCard({
  content,
  saver,
}: {
  content: Content;
  saver?: { userId: string; name: string };
}) {
  return (
    <li className="flex flex-col gap-2 rounded-xl border border-border p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-foreground">{content.place.name}</p>
          <p className="text-sm text-muted-foreground">
            {content.area} · {CATEGORY_LABEL[content.category]}
          </p>
        </div>
        {saver && (
          <span className="flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground">
            <UserAvatar user={saver} size="sm" />
            {saver.name}
          </span>
        )}
      </div>

      {content.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {content.tags.map((tag) => (
            <Badge key={tag} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      <a
        href={content.url}
        target="_blank"
        rel="noreferrer"
        className="inline-flex w-fit items-center gap-1 text-sm text-primary hover:underline"
      >
        원본 보기 <ExternalLink className="size-3.5" />
      </a>
    </li>
  );
}
