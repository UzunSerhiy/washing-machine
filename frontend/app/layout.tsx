import type { Metadata } from 'next';
import { Geist, Geist_Mono, Inter } from 'next/font/google';
import './globals.css';
import { cn } from '@/lib/utils';
import { QueryProvider } from '@/providers/query-provider';
import { MachineNavigation } from '@/components/machine/machine-navigation';
import { MachineIOControls } from '@/components/machine/machine-io-controls';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Washing Machine',
  description: 'Washing machine control panel',
};

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html
      lang="ru"
      className={cn(
        'h-full',
        'antialiased',
        geistSans.variable,
        geistMono.variable,
        'font-sans',
        inter.variable,
      )}
    >
      <body>
        <QueryProvider>
          <div className="mx-auto max-w-6xl space-y-4 px-4 pt-5 md:px-8">
            <MachineIOControls />
            <MachineNavigation />
          </div>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
