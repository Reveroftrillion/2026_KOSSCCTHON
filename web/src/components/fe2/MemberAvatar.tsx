import { cn } from '@/lib/utils'

interface Props {
  name: string
  size?: 'sm' | 'md'
  className?: string
}

// 임시 아바타. FE1의 공통 UserAvatar(C-05)가 나오면 교체한다.
export default function MemberAvatar({ name, size = 'md', className }: Props) {
  return (
    <span
      title={name}
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full bg-blue-600 font-semibold text-white',
        size === 'sm' ? 'h-6 w-6 text-xs' : 'h-9 w-9 text-sm',
        className,
      )}
    >
      {name.slice(0, 1)}
    </span>
  )
}
