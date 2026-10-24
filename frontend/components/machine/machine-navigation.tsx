'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const tabs = [
  { href: '/manual', label: 'Manual' },
  { href: '/auto', label: 'Auto' },
  { href: '/calibration', label: 'Calibration' },
] as const;

export function MachineNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="Machine modes" className="grid grid-cols-3 gap-1 rounded-xl border bg-muted/50 p-1">
      {tabs.map(({ href, label }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={`rounded-lg px-3 py-3 text-center text-sm font-semibold transition-colors sm:text-base ${
              active
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
