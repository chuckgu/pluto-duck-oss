'use client';

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CopyIcon, RefreshCcwIcon } from 'lucide-react';

import { ConversationList } from '../../components/chat';
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
  Message,
  MessageAvatar,
  MessageContent,
  Response,
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
  PromptInput,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTools,
  Actions,
  Action,
  Loader,
  Suggestions,
  Suggestion,
  type PromptInputMessage,
} from '../../components/ai-elements';
import {
  createConversation,
  fetchChatSession,
  fetchChatSessions,
  appendMessage,
  deleteConversation,
  type AppendMessageResponse,
  type ChatSessionDetail,
  type ChatSessionSummary,
} from '../../lib/chatApi';
import { useAgentStream } from '../../hooks/useAgentStream';
import type { AgentEventAny } from '../../types/agent';

const suggestions = [
  'Show me top 5 products by revenue',
  'List customers from last month',
  'Analyze sales trends by region',
  'What are the latest orders?',
];

export default function WorkspacePage() {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSessionSummary | null>(null);
  const [detail, setDetail] = useState<ChatSessionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const lastRunIdRef = useRef<string | null>(null);
  const lastCompletedRunRef = useRef<string | null>(null);
  const { events: streamEvents, status: streamStatus, reset: resetStream } = useAgentStream({
    runId: activeRunId ?? undefined,
    eventsPath: activeRunId ? `/api/v1/agent/${activeRunId}/events` : undefined,
    autoReconnect: false,
  });

  const pickActiveRunId = useCallback((session: ChatSessionSummary | null | undefined) => {
    if (!session) return null;
    return session.status === 'active' ? session.run_id ?? null : null;
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      console.info('[Workspace] Loading sessions');
      const data = await fetchChatSessions();
      console.info('[Workspace] Sessions fetched', data);
      setSessions(data);
      setActiveSession(prev => {
        if (data.length === 0) {
          console.info('[Workspace] No sessions found');
          setActiveRunId(null);
          return null;
        }
        if (!prev) {
          console.info('[Workspace] Selecting first session', data[0]);
          setActiveRunId(pickActiveRunId(data[0]));
          return data[0];
        }
        const match = data.find(session => session.id === prev.id);
        console.info('[Workspace] Matching session result', match ?? prev);
        setActiveRunId(pickActiveRunId(match ?? prev));
        return match ?? prev;
      });
    } catch (error) {
      console.error('Failed to load sessions', error);
    }
  }, [pickActiveRunId]);

  const fetchDetail = useCallback(async (sessionId: string, includeEvents: boolean = true) => {
    console.info('[Workspace] Fetching session detail', sessionId, { includeEvents });
    const response = await fetchChatSession(sessionId, includeEvents);
    console.info('[Workspace] Session detail response', response);
    return response;
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (!activeSession) {
      setDetail(null);
      if (!isCreatingConversation) {
        setActiveRunId(null);
        lastRunIdRef.current = null;
        lastCompletedRunRef.current = null;
      }
      return;
    }
    const currentSession = activeSession;
    const sessionId = currentSession.id;
    let cancelled = false;
    async function loadDetail() {
      try {
        setLoading(true);
        const response = await fetchDetail(sessionId, true);
        if (!cancelled) {
          setDetail(response);
          const nextRunId = response.status === 'active' ? response.run_id ?? currentSession.run_id ?? null : null;
          setActiveRunId(nextRunId);
          setActiveSession(prev =>
            prev && prev.id === sessionId
              ? { ...prev, run_id: response.run_id ?? prev.run_id, status: response.status }
              : prev,
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [activeSession?.id, fetchDetail, isCreatingConversation]);

  const events = useMemo<AgentEventAny[]>(() => streamEvents, [streamEvents]);
  const reasoningEvents = useMemo(() => events.filter(e => e.type === 'reasoning'), [events]);
  const runHasEnded = useMemo(
    () =>
      events.some(event =>
        (event.type === 'run' && event.subtype === 'end') ||
        (event.type === 'message' && event.subtype === 'final'),
      ),
    [events],
  );

  const isStreaming = (streamStatus === 'streaming' || streamStatus === 'connecting') && !runHasEnded;
  const status = streamStatus === 'error' ? 'error' : isStreaming ? 'streaming' : 'ready';

  useEffect(() => {
    console.info('[Workspace] Stream status changed', streamStatus);
  }, [streamStatus]);

  useEffect(() => {
    if (!activeRunId) {
      lastRunIdRef.current = null;
      lastCompletedRunRef.current = null;
      return;
    }
    if (activeRunId !== lastRunIdRef.current) {
      lastRunIdRef.current = activeRunId;
      lastCompletedRunRef.current = null;
      resetStream();
    }
  }, [activeRunId, resetStream]);

  useEffect(() => {
    if (streamEvents.length === 0) return;
    const latest = streamEvents[streamEvents.length - 1];
    console.info('[Workspace] New stream event', latest, { totalEvents: streamEvents.length });
  }, [streamEvents]);

  useEffect(() => {
    if (!activeSession || !activeRunId || streamEvents.length === 0) {
      return;
    }
    const latest = streamEvents[streamEvents.length - 1];
    if (
      (latest.type === 'run' && latest.subtype === 'end') ||
      (latest.type === 'message' && latest.subtype === 'final')
    ) {
      if (lastCompletedRunRef.current === activeRunId) {
        return;
      }
      lastCompletedRunRef.current = activeRunId;
      console.info('[Workspace] Run completed, refreshing session detail');
      void (async () => {
        try {
          setLoading(true);
          const currentSession = activeSession;
          const response = await fetchDetail(currentSession.id, true);
          setDetail(response);
          const nextRunId = response.status === 'active' ? response.run_id ?? activeRunId : null;
          setActiveSession(prev =>
            prev && prev.id === currentSession.id
              ? { ...prev, run_id: response.run_id ?? prev.run_id, status: response.status }
              : prev,
          );
          setActiveRunId(nextRunId);
          void loadSessions();
        } catch (error) {
          console.error('[Workspace] Failed to refresh detail after run end', error);
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [activeSession, activeRunId, fetchDetail, loadSessions, streamEvents]);

  const handleSelectSession = useCallback((session: ChatSessionSummary) => {
    resetStream();
    setIsCreatingConversation(false);
    setDetail(null);
    setActiveSession(session);
    setActiveRunId(session.run_id ?? null);
  }, [resetStream]);

  const handleDeleteSession = useCallback(
    async (session: ChatSessionSummary) => {
      try {
        await deleteConversation(session.id);
        setSessions(prev => prev.filter(item => item.id !== session.id));
        if (activeSession?.id === session.id) {
          setActiveSession(null);
          setActiveRunId(null);
          setDetail(null);
        }
        void loadSessions();
      } catch (error) {
        console.error('[Workspace] Failed to delete conversation', error);
      }
    },
    [activeSession, loadSessions],
  );

  const handleNewConversation = useCallback(() => {
    setActiveSession(null);
    setActiveRunId(null);
    setDetail(null);
    setInput('');
    setIsCreatingConversation(true);
    resetStream();
  }, [resetStream]);

  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      const prompt = message.text?.trim();
      if (!prompt) return;

      setInput('');
      resetStream();

      try {
        if (!activeSession) {
          console.info('[Workspace] Creating conversation for prompt', prompt);
          setIsCreatingConversation(false);
          const response = await createConversation({ question: prompt });
          console.info('[Workspace] Conversation created', response);
          const nowIso = new Date().toISOString();
          const newSession: ChatSessionSummary = {
            id: response.conversation_id ?? response.id,
            title: prompt ? prompt.slice(0, 80) : null,
            status: 'active',
            created_at: nowIso,
            updated_at: nowIso,
            last_message_preview: prompt ? prompt.slice(0, 160) : null,
            run_id: response.run_id,
            events_url: response.events_url,
          };
          setActiveSession(newSession);
          setActiveRunId(response.run_id ?? null);
          setSessions(prev => {
            const filtered = prev.filter(session => session.id !== newSession.id);
            return [newSession, ...filtered];
          });
          void loadSessions();
          return;
        }

        console.info('[Workspace] Appending message to existing conversation', activeSession.id);
        const currentSession = activeSession;
        const response: AppendMessageResponse = await appendMessage(currentSession.id, { role: 'user', content: { text: prompt } });
        console.info('[Workspace] Follow-up queued', response);
        const nextRunId = response.run_id ?? currentSession.run_id ?? null;
        setActiveRunId(nextRunId);
        setActiveSession(prev =>
          prev && prev.id === currentSession.id
            ? {
                ...prev,
                run_id: response.run_id ?? prev.run_id,
                status: 'active',
                updated_at: new Date().toISOString(),
                last_message_preview: prompt.slice(0, 160) || prev.last_message_preview,
              }
            : prev,
        );
        setDetail(prev =>
          prev
            ? {
                ...prev,
                messages: [
                  ...prev.messages,
                  {
                    id: `temp-${Date.now()}`,
                    role: 'user',
                    content: { text: prompt },
                    created_at: new Date().toISOString(),
                    seq: prev.messages.length + 1,
                  },
                ],
              }
            : prev,
        );
        void loadSessions();
      } catch (error) {
        console.error('Failed to submit message', error);
      }
    },
    [activeSession, createConversation, loadSessions, resetStream],
  );

  const handleSuggestionClick = useCallback((suggestion: string) => {
    setInput(suggestion);
    textareaRef.current?.focus();
  }, []);

  const handleRegenerate = useCallback(() => {
    console.log('Regenerate clicked');
  }, []);

  const handleCopy = useCallback((text: string) => {
    void navigator.clipboard.writeText(text);
  }, []);

  const messages = detail?.messages || [];
  const hasReasoning = reasoningEvents.length > 0;
  const reasoningText = reasoningEvents
    .map(event => {
      const content = event.content as any;
      return content && typeof content === 'object' && content.reason ? String(content.reason) : '';
    })
    .filter(Boolean)
    .join('\n\n');

  return (
    <div className="flex h-screen w-full flex-1">
      {/* Sidebar conversation list */}
      <aside className="hidden w-80 border-r border-border bg-muted/20 px-4 py-6 lg:flex lg:flex-col">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Conversations</h2>
          <button
            type="button"
            className="text-xs font-medium text-primary hover:text-primary/80"
            onClick={() => void loadSessions()}
          >
            Refresh
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <ConversationList sessions={sessions} activeId={activeSession?.id} onSelect={handleSelectSession} onDelete={handleDeleteSession} />
        </div>
        <button
          type="button"
          className="mt-4 w-full rounded-lg border border-primary/40 bg-primary/10 px-3 py-2 text-sm font-semibold text-primary hover:bg-primary/20"
          onClick={handleNewConversation}
        >
          New conversation
        </button>
      </aside>

      {/* Main chat area */}
      <div className="relative flex size-full flex-col divide-y overflow-hidden bg-muted/5">
        <Conversation>
          <ConversationContent>
            {loading && (
              <div className="px-4 py-6">
                <div className="mx-auto max-w-3xl">
                  <Loader />
                </div>
              </div>
            )}

            {messages.map((message, messageIndex) => (
              <div key={message.id} className="group px-4 py-6">
                <div className="mx-auto max-w-3xl">
                  {message.role === 'user' ? (
                    /* User message - simple bubble */
                    <div className="flex justify-end">
                      <div className="rounded-2xl bg-primary px-4 py-3 text-primary-foreground">
                        <p className="text-sm">
                          {typeof message.content === 'object' && message.content?.text
                            ? message.content.text
                            : typeof message.content === 'string'
                              ? message.content
                              : JSON.stringify(message.content)}
                        </p>
                      </div>
                    </div>
                  ) : (
                    /* Assistant message - streaming response with avatar */
                    <div className="flex gap-4">
                      <MessageAvatar name="Agent" src="https://github.com/openai.png" />
                      <div className="flex-1 space-y-4">
                        {/* Show reasoning for assistant messages */}
                        {hasReasoning && messageIndex === messages.length - 1 && (
                          <Reasoning isStreaming={isStreaming} defaultOpen={true}>
                            <ReasoningTrigger />
                            <ReasoningContent>{reasoningText}</ReasoningContent>
                          </Reasoning>
                        )}

                        {/* Message content - no bubble, just text */}
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          <Response>
                            {typeof message.content === 'object' && message.content?.text
                              ? message.content.text
                              : typeof message.content === 'string'
                                ? message.content
                                : JSON.stringify(message.content)}
                          </Response>
                        </div>

                        {/* Actions for last assistant message */}
                        {messageIndex === messages.length - 1 && (
                          <Actions className="opacity-0 transition-opacity group-hover:opacity-100">
                            <Action onClick={handleRegenerate} label="Retry">
                              <RefreshCcwIcon className="size-3" />
                            </Action>
                            <Action
                              onClick={() => {
                                const text =
                                  typeof message.content === 'object' && message.content?.text
                                    ? message.content.text
                                    : JSON.stringify(message.content);
                                handleCopy(text);
                              }}
                              label="Copy"
                            >
                              <CopyIcon className="size-3" />
                            </Action>
                          </Actions>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Loading indicator during streaming */}
            {isStreaming && messages.length > 0 && (
              <div className="px-4 py-6">
                <div className="mx-auto max-w-3xl">
                  <Loader />
                </div>
              </div>
            )}

            {/* Empty state */}
            {!loading && messages.length === 0 && (
              <div className="flex flex-1 items-center justify-center px-4">
                <div className="mx-auto max-w-3xl">
                  <p className="text-sm text-muted-foreground">
                    {activeSession ? 'No messages yet.' : 'Start a new conversation below.'}
                  </p>
                </div>
              </div>
            )}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        {/* Input area with suggestions */}
        <div className="grid shrink-0 gap-4 pt-4">
          {messages.length === 0 && (
            <div className="px-4">
              <Suggestions className="mx-auto max-w-3xl">
                {suggestions.map(suggestion => (
                  <Suggestion key={suggestion} onClick={() => handleSuggestionClick(suggestion)} suggestion={suggestion} />
                ))}
              </Suggestions>
            </div>
          )}
          <div className="w-full px-4 pb-4">
            <div className="mx-auto max-w-3xl">
              <PromptInput onSubmit={handleSubmit}>
                <PromptInputBody>
                  <PromptInputTextarea
                    value={input}
                    onChange={event => setInput(event.target.value)}
                    ref={textareaRef}
                    placeholder={activeSession ? 'Continue this conversation...' : 'Ask a question...'}
                  />
                </PromptInputBody>
                <PromptInputFooter>
                  <PromptInputTools />
                  <PromptInputSubmit disabled={!input.trim() || isStreaming} status={status} />
                </PromptInputFooter>
              </PromptInput>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
