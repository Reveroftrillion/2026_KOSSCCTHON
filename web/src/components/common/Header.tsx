'use client';

import Link from 'next/link';
import { UserRound } from 'lucide-react';
import { useUser } from '@/lib/user-context';
import { cn } from '@/lib/utils';
import { UserAvatar } from './UserAvatar';

// 데모 유저(3명) 전환 UI. 클릭한 유저로 전역 currentUser가 바뀌어
// 개인 취향/장바구니 등 유저 종속 데이터가 함께 바뀐다 (C-04 완료 기준).
export function Header() {
  const { currentUser, users, setCurrentUserId } = useUser();

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/80 px-4 py-3 backdrop-blur">
      <Link href="/" className="text-base font-extrabold tracking-tight text-secondary-foreground">
        TripClip
      </Link>
      <div className="flex items-center gap-3">
        <Link
          href="/me/preferences"
          aria-label="내 취향 프로필"
          className="text-muted-foreground transition hover:text-foreground"
        >
          <UserRound className="size-5" />
        </Link>
        <div className="flex items-center gap-1.5" role="group" aria-label="데모 유저 전환">
          {users.map((user) => (
            <button
              key={user.userId}
              type="button"
              onClick={() => setCurrentUserId(user.userId)}
              aria-pressed={user.userId === currentUser.userId}
              className={cn(
                'rounded-full outline-none ring-primary transition',
                'focus-visible:ring-2 aria-[pressed=true]:ring-2 aria-[pressed=false]:opacity-50'
              )}
            >
              <UserAvatar user={user} size="sm" />
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
