'use client';

import type { ChatSessionSummary } from '../../lib/chatApi';

export interface ConversationSummary {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_message_preview: string | null;
}

interface ConversationListProps {
  sessions: ChatSessionSummary[];
  activeId?: string;
  onSelect?: (conversation: ChatSessionSummary) => void;
  onDelete?: (conversation: ChatSessionSummary) => void;
  loading?: boolean;
  error?: string | null;
}

export function ConversationList({ sessions, activeId, onSelect, onDelete, loading = false, error }: ConversationListProps) {
  return (
    <div className="space-y-2">
      {loading && <p className="text-xs text-muted-foreground">Loading...</p>}
      {error && <p className="text-xs text-destructive">{error}</p>}
      {!loading && sessions.length === 0 && <p className="text-xs text-muted-foreground">No conversations yet.</p>}
      {sessions.map(session => (
        <div
          key={session.id}
          className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition ${
            session.id === activeId
              ? 'border-primary/60 bg-primary/10 text-primary'
              : 'border-border bg-card/40 hover:border-primary/40'
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <button
              type="button"
              onClick={() => onSelect?.(session)}
              className="flex-1 text-left"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground">{session.title || 'Untitled'}</span>
                <span className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                  {session.status}
                </span>
              </div>
              {session.last_message_preview && (
                <p className="mt-1 line-clamp-2 text-muted-foreground">{session.last_message_preview}</p>
              )}
            </button>
            <button
              type="button"
              className="rounded-md p-1 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
              onClick={() => onDelete?.(session)}
              aria-label="Delete conversation"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
