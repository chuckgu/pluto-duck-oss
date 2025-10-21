'use client';

import Link from 'next/link';

import { getBackendUrl } from '../lib/api';

export default function Home() {
  const backendUrl = getBackendUrl();

  return (
    <main className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-background/60 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Pluto-Duck Agent Studio</h1>
            <p className="text-sm text-muted-foreground">
              Local-first analytics powered by DuckDB, dbt, and LangGraph. Backend: <code className="text-primary">{backendUrl}</code>
            </p>
          </div>
          <nav className="flex gap-3 text-sm">
            <Link
              href="/workspace"
              className="rounded border border-primary px-3 py-1.5 font-medium text-primary transition hover:bg-primary hover:text-primary-foreground"
            >
              Open Workspace
            </Link>
            <Link
              href="https://github.com/pluto-duck/pluto_duck_oss"
              className="rounded border border-border px-3 py-1.5 font-medium text-foreground transition hover:border-primary/40"
            >
              View Docs
            </Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-6 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-border bg-card/60 p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-foreground">What&apos;s inside</h2>
            <ul className="mt-4 space-y-3 text-sm text-foreground">
              <li>• Persistent chat history stored in DuckDB</li>
              <li>• Real-time LangGraph event streaming</li>
              <li>• Data source onboarding and dbt project configuration</li>
              <li>• Agent runs with SQL verification and results playback</li>
            </ul>
          </div>

          <div className="rounded-xl border border-border bg-card/60 p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-foreground">Next steps</h2>
            <ol className="mt-4 space-y-3 text-sm text-foreground">
              <li>1. Launch the backend (<code className="text-primary">pluto-duck run</code>) to ensure API availability.</li>
              <li>2. Open the workspace, configure data sources, and start a conversation.</li>
              <li>3. Stream reasoning/tool events live or revisit historical runs anytime.</li>
            </ol>
            <div className="mt-6 flex gap-3">
              <Link
                href="/workspace"
                className="flex-1 rounded-lg bg-primary px-4 py-2 text-center text-sm font-semibold text-primary-foreground shadow transition hover:bg-primary/90"
              >
                Go to workspace
              </Link>
              <a
                href="https://github.com/pluto-duck/pluto_duck_oss/tree/main/docs"
                className="flex-1 rounded-lg border border-border px-4 py-2 text-center text-sm font-semibold text-foreground transition hover:border-primary/40"
                target="_blank"
                rel="noopener noreferrer"
              >
                Read docs
              </a>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card/40 p-6 text-sm text-muted-foreground">
          <p>
            Tip: open the workspace in one tab and run <code className="text-primary">pluto-duck agent-stream &quot;&lt;question&gt;&quot;</code> in your terminal to
            see matching SSE events. The new chat UI consumes the same endpoints so you can debug and iterate locally.
          </p>
        </div>
      </section>
    </main>
  );
}
