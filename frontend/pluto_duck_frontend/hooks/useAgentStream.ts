'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import type { AgentEventAny } from '../types/agent';
import { getBackendUrl } from '../lib/api';

export interface UseAgentStreamOptions {
  runId?: string;
  eventsPath?: string; // e.g. /api/v1/agent/{run_id}/events
  autoReconnect?: boolean;
  reconnectIntervalMs?: number;
}

export interface UseAgentStreamResult {
  events: AgentEventAny[];
  status: 'idle' | 'connecting' | 'streaming' | 'error';
  error?: string;
  reset: () => void;
}

export function useAgentStream({
  runId,
  eventsPath,
  autoReconnect = true,
  reconnectIntervalMs = 2000,
}: UseAgentStreamOptions): UseAgentStreamResult {
  const [events, setEvents] = useState<AgentEventAny[]>([]);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'streaming' | 'error'>(runId ? 'connecting' : 'idle');
  const [error, setError] = useState<string | undefined>();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  const reset = useCallback(() => {
    setEvents([]);
    setError(undefined);
    setStatus(runId ? 'connecting' : 'idle');
  }, [runId]);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!runId || !eventsPath) {
      cleanup();
      setStatus('idle');
      return;
    }

    const backendUrl = getBackendUrl();
    const url = `${backendUrl}${eventsPath.startsWith('/') ? eventsPath : `/${eventsPath}`}`;

    setStatus('connecting');
    const source = new EventSource(url);
    eventSourceRef.current = source;

    source.onopen = () => {
      setStatus('streaming');
      setError(undefined);
    };

    source.onmessage = event => {
      try {
        const parsed = JSON.parse(event.data) as AgentEventAny;
        setEvents(prev => [...prev, parsed]);
        
        // If run ended, close connection and set status to idle
        if (parsed.type === 'run' && parsed.subtype === 'end') {
          setStatus('idle');
          source.close();
        }
      } catch (err) {
        console.error('Failed to parse agent event', err);
      }
    };

    source.onerror = () => {
      setStatus('error');
      setError('Streaming connection lost.');
      source.close();

      if (autoReconnect && reconnectTimerRef.current === null) {
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          reset();
        }, reconnectIntervalMs);
      }
    };

    return () => {
      cleanup();
    };
  }, [runId, eventsPath, autoReconnect, reconnectIntervalMs, cleanup, reset]);

  return { events, status, error, reset };
}
