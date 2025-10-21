import type { ReactNode } from 'react';

import './globals.css';

export const metadata = {
  title: 'Pluto-Duck Agent Studio',
  description: 'Local-first analytics assistant with DuckDB, dbt, and LangGraph',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen">
        <div className="flex min-h-screen flex-col">
          {children}
        </div>
      </body>
    </html>
  );
}
