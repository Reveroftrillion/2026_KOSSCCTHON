'use client';

import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { createContent } from '@/lib/api';
import { useUser } from '@/lib/user-context';
import { LoadingSteps, ErrorState } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

type Platform = 'instagram' | 'youtube' | 'tiktok' | 'other';

const PLATFORM_PATTERNS: [RegExp, 'instagram' | 'youtube' | 'tiktok'][] = [
  [/instagram\.com/i, 'instagram'],
  [/(youtube\.com|youtu\.be)/i, 'youtube'],
  [/tiktok\.com/i, 'tiktok'],
];

const PLATFORM_LABEL: Record<Platform, string> = {
  instagram: 'Instagram',
  youtube: 'YouTube',
  tiktok: 'TikTok',
  other: '기타',
};

// URL 형식만 통과하면 플랫폼 뱃지를 미리 보여준다 (실제 분석은 서버/mock의 analyzeUrl이 담당).
function detectPlatform(url: string): Platform | null {
  if (!z.string().url().safeParse(url).success) return null;
  for (const [pattern, platform] of PLATFORM_PATTERNS) {
    if (pattern.test(url)) return platform;
  }
  return 'other';
}

const formSchema = z.object({
  url: z.string().min(1, '링크를 입력해주세요.').url('올바른 URL 형식이 아니에요.'),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof formSchema>;

export default function AddContentPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const router = useRouter();
  const { currentUser } = useUser();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { url: '', note: '' },
  });

  // watch()가 이미 매 입력마다 리렌더를 구독하므로 useMemo로 감쌀 필요가 없다.
  const platform = detectPlatform(watch('url'));

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      createContent({
        url: values.url,
        userId: currentUser.userId,
        tripId,
        note: values.note?.trim() || undefined,
      }),
    onSuccess: (content) => {
      router.push(`/trips/${tripId}/review/${content.contentId}`);
    },
  });

  if (mutation.isPending) {
    return (
      <LoadingSteps
        steps={['링크 확인 중', 'AI로 장소 분석 중']}
        className="mx-auto w-full max-w-md flex-1"
      />
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-lg font-semibold text-foreground">숏폼 링크 저장</h1>
        <p className="text-sm text-muted-foreground">
          릴스·쇼츠·틱톡 링크를 붙여넣으면 AI가 장소를 분석해요.
        </p>
      </div>

      {mutation.isError && (
        <ErrorState
          message={
            mutation.error instanceof Error
              ? mutation.error.message
              : '분석에 실패했어요. 링크를 확인하고 다시 시도해 주세요.'
          }
          onRetry={() => mutation.reset()}
        />
      )}

      <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-5">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="url">숏폼 링크</Label>
            {platform && <Badge variant="secondary">{PLATFORM_LABEL[platform]}</Badge>}
          </div>
          <Input id="url" placeholder="https://www.instagram.com/reel/..." {...register('url')} />
          {errors.url && <p className="text-sm text-destructive">{errors.url.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="note">보정 입력 (선택)</Label>
          <Textarea
            id="note"
            placeholder="게시글 내용이나 해시태그를 붙여넣으면 분석 정확도가 올라가요. 예: 성수 감성 카페 #디저트 #데이트"
            rows={4}
            {...register('note')}
          />
        </div>

        <Button type="submit" size="lg">
          저장하고 분석하기
        </Button>
      </form>
    </div>
  );
}
