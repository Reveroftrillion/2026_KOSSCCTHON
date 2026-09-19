'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// 5-3 파이프라인 문구(예: "그룹 취향 분석 중 → 일정 생성 중 → 균형 점검 중")를 순차 표시하는 로딩 UI.
export function LoadingSteps({
  steps,
  stepDurationMs = 900,
  className,
}: {
  steps: string[];
  stepDurationMs?: number;
  className?: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [prevSteps, setPrevSteps] = useState(steps);

  // steps 배열이 바뀌면(다른 단계 목록으로 재사용되면) 렌더링 도중 바로 초기화한다.
  // (참고: https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes)
  if (steps !== prevSteps) {
    setPrevSteps(steps);
    setActiveIndex(0);
  }

  useEffect(() => {
    if (steps.length <= 1) return;
    const timer = setInterval(() => {
      setActiveIndex((i) => Math.min(i + 1, steps.length - 1));
    }, stepDurationMs);
    return () => clearInterval(timer);
  }, [steps, stepDurationMs]);

  return (
    <div className={cn('flex flex-col items-center gap-4 py-10 text-center', className)}>
      <Loader2 className="size-6 animate-spin text-primary" />
      <ol className="flex flex-col gap-1.5">
        {steps.map((step, i) => (
          <li
            key={step}
            className={cn(
              'text-sm transition-colors',
              i < activeIndex && 'text-muted-foreground line-through',
              i === activeIndex && 'font-medium text-foreground',
              i > activeIndex && 'text-muted-foreground/60'
            )}
          >
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}
