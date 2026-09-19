import { cn } from '@/lib/utils';
import type { User } from '@/lib/types';

const COLOR_CLASSES = [
  'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300',
  'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
  'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300',
  'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300',
];

function colorForUser(userId: string) {
  let hash = 0;
  for (const ch of userId) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return COLOR_CLASSES[hash % COLOR_CLASSES.length];
}

const SIZE_CLASSES = { sm: 'size-6 text-xs', md: 'size-8 text-sm', lg: 'size-10 text-base' } as const;

export function UserAvatar({
  user,
  size = 'md',
  className,
}: {
  user: Pick<User, 'userId' | 'name'>;
  size?: keyof typeof SIZE_CLASSES;
  className?: string;
}) {
  return (
    <span
      title={user.name}
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full font-medium',
        SIZE_CLASSES[size],
        colorForUser(user.userId),
        className
      )}
    >
      {user.name.slice(0, 1)}
    </span>
  );
}
