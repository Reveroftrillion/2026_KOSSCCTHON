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
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

function isYouTubeUrl(url: string): boolean {
  if (!z.string().url().safeParse(url).success) return false;

  try {
    const parsed = new URL(url);

    return [
      'youtube.com',
      'www.youtube.com',
      'm.youtube.com',
      'youtu.be',
    ].includes(parsed.hostname);
  } catch {
    return false;
  }
}

const formSchema = z.object({
  url: z
    .string()
    .min(1, 'YouTube 링크를 입력해주세요.')
    .url('올바른 URL 형식이 아니에요.')
    .refine(
      (url) => isYouTubeUrl(url),
      '현재는 YouTube Shorts만 지원해요.',
    ),
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
    defaultValues: { url: '' },
  });

  // watch()가 이미 매 입력마다 리렌더를 구독하므로 useMemo로 감쌀 필요가 없다.
  const url = watch('url');
  const isYouTube = isYouTubeUrl(url);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      createContent({
        url: values.url,
        userId: currentUser.userId,
        tripId,
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
        <h1 className="text-lg font-semibold text-foreground">YouTube Shorts 링크 저장</h1>
        <p className="text-sm text-muted-foreground">
          YouTube Shorts 링크를 붙여넣으면 AI가 장소를 분석해요.
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
            <Label htmlFor="url">YouTube Shorts 링크</Label>
            {isYouTube && <Badge variant="secondary">YouTube</Badge>}
          </div>
          <Input id="url" placeholder="https://www.youtube.com/shorts/..." {...register('url')} />
          {errors.url && <p className="text-sm text-destructive">{errors.url.message}</p>}
        </div>

        <Button type="submit" size="lg">
          저장하고 분석하기
        </Button>
      </form>
    </div>
  );
}
