import { cn } from '@/lib/utils';
import type { PreferenceItem } from '@/lib/types';

// 3장 작업 규칙: 원점수(score)는 절대 표시하지 않고 normalized(0~100)만 노출한다.
export function PreferenceBar({
  item,
  highlighted,
  className,
}: {
  item: Pick<PreferenceItem, 'label' | 'normalized' | 'evidenceCount'>;
  highlighted?: boolean;
  className?: string;
}) {
  const width = Math.min(100, Math.max(0, item.normalized));
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className={cn('font-medium text-foreground', highlighted && 'text-primary')}>{item.label}</span>
        <span className="text-muted-foreground">근거 {item.evidenceCount}건</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full bg-primary transition-[width] duration-500', highlighted && 'bg-emerald-500')}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
