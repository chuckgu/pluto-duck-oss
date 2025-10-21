import type { ReactNode } from 'react';

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return <div className="flex min-h-[calc(100vh-4rem)] flex-1 bg-background">{children}</div>;
}
