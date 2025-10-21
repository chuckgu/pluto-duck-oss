'use client';

import { Response, Reasoning, ReasoningTrigger, ReasoningContent } from '../ai-elements';
import type { AgentEventAny } from '../../types/agent';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: any;
  created_at: string;
}

interface TranscriptProps {
  messages: Message[];
  events: AgentEventAny[];
}

export function Transcript({ messages, events }: TranscriptProps) {
  const reasoningEvents = events.filter(event => event.type === 'reasoning');
  const hasActiveReasoning = reasoningEvents.some(event => event.subtype === 'chunk' || event.subtype === 'start');

  return (
    <div className="flex-1 space-y-4 overflow-y-auto">
      {messages.map(message => (
        <article
          key={message.id}
          className={`rounded-lg border p-4 text-sm shadow-sm ${
            message.role === 'user'
              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-50'
              : 'border-slate-800 bg-slate-900/70 text-slate-100'
          }`}
        >
          <header className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-400">
            <span>{message.role}</span>
            <time className="font-normal">{new Date(message.created_at).toLocaleTimeString()}</time>
          </header>
          <MessageContent content={message.content} />
        </article>
      ))}

      {reasoningEvents.length > 0 && (
        <Reasoning isStreaming={hasActiveReasoning} defaultOpen={true}>
          <ReasoningTrigger />
          <ReasoningContent>
            {reasoningEvents
              .map(event => {
                const content = event.content as any;
                return content && typeof content === 'object' && content.reason ? String(content.reason) : '';
              })
              .join('\n')}
          </ReasoningContent>
        </Reasoning>
      )}

      {events
        .filter(event => event.type === 'tool' || event.type === 'message')
        .map((event, index) => (
          <article
            key={`${event.type}-${event.timestamp}-${index}`}
            className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-slate-300"
          >
            <header className="mb-1 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide text-amber-400">
              <span>
                {event.type}.{event.subtype}
              </span>
              {event.timestamp && <time className="font-normal text-slate-500">{new Date(event.timestamp).toLocaleTimeString()}</time>}
            </header>
            <ToolContent content={event.content} />
          </article>
        ))}
    </div>
  );
}

function MessageContent({ content }: { content: any }) {
  if (content == null) {
    return <p className="text-slate-500">(empty)</p>;
  }

  if (typeof content === 'string') {
    return <Response>{content}</Response>;
  }

  if (content.text && typeof content.text === 'string') {
    return <Response>{content.text}</Response>;
  }

  return (
    <pre className="overflow-x-auto rounded bg-slate-950/90 p-2 text-[11px] text-slate-200">
      <code>{JSON.stringify(content, null, 2)}</code>
    </pre>
  );
}

function ToolContent({ content }: { content: any }) {
  if (content == null) {
    return <p className="text-slate-500">(empty)</p>;
  }

  if (typeof content === 'string') {
    return <p className="whitespace-pre-wrap font-mono text-[11px]">{content}</p>;
  }

  return (
    <pre className="overflow-x-auto rounded bg-slate-950/90 p-2 text-[11px] text-emerald-200">
      <code>{JSON.stringify(content, null, 2)}</code>
    </pre>
  );
}
