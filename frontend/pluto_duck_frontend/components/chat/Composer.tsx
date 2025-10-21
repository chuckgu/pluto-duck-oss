'use client';

import { FormEvent, useState } from 'react';

interface ComposerProps {
  onSubmit: (text: string) => Promise<void> | void;
  disabled?: boolean;
  placeholder?: string;
  submitting?: boolean;
}

export function Composer({ onSubmit, disabled = false, placeholder, submitting = false }: ComposerProps) {
  const [text, setText] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    await onSubmit(trimmed);
    setText('');
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/70 p-4 shadow-lg">
      <textarea
        className="min-h-[120px] w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none"
        placeholder={placeholder || 'Ask a question for the agent...'}
        value={text}
        onChange={event => setText(event.target.value)}
        disabled={disabled || submitting}
      />
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Shift+Enter to add a newline.</span>
        <button
          type="submit"
          disabled={disabled || submitting}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {submitting ? 'Sending…' : 'Send'}
        </button>
      </div>
    </form>
  );
}
