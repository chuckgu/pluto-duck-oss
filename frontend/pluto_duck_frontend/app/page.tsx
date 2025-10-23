'use client';

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CopyIcon, RefreshCcwIcon, PlusIcon, SettingsIcon, DatabaseIcon } from 'lucide-react';

import { ConversationList, SettingsModal } from '../components/chat';
import {
  DataSourcesView,
  ImportCSVModal,
  ImportParquetModal,
  ImportPostgresModal,
  ImportSQLiteModal,
} from '../components/data-sources';
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
  PromptInputModelSelect,
  PromptInputModelSelectTrigger,
  PromptInputModelSelectValue,
  PromptInputModelSelectContent,
  PromptInputModelSelectItem,
  Actions,
  Action,
  Loader,
  Suggestions,
  Suggestion,
  type PromptInputMessage,
} from '../components/ai-elements';
import {
  createConversation,
  fetchChatSession,
  fetchChatSessions,
  appendMessage,
  deleteConversation,
  type AppendMessageResponse,
  type ChatSessionDetail,
  type ChatSessionSummary,
} from '../lib/chatApi';
import { fetchSettings } from '../lib/settingsApi';
import { fetchDataSources, type DataSource } from '../lib/dataSourcesApi';
import { useAgentStream } from '../hooks/useAgentStream';
import { useBackendStatus } from '../hooks/useBackendStatus';
import type { AgentEventAny } from '../types/agent';

const suggestions = [
  'Show me top 5 products by revenue',
  'List customers from last month',
  'Analyze sales trends by region',
];

const MODELS = [
  { id: 'gpt-5', name: 'GPT-5' },
  { id: 'gpt-5-mini', name: 'GPT-5 Mini' },
];

const MAX_PREVIEW_LENGTH = 160;

type ViewMode = 'chat' | 'data-sources';

function extractTextFromUnknown(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    try {
      const parsed = JSON.parse(trimmed);
      return extractTextFromUnknown(parsed);
    } catch {
      return trimmed;
    }
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const result = extractTextFromUnknown(item);
      if (result) return result;
    }
    return null;
  }
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const directKeys = ['final_answer', 'answer', 'text', 'summary', 'message', 'preview'];
    for (const key of directKeys) {
      const candidate = obj[key];
      if (typeof candidate === 'string' && candidate.trim()) {
        return candidate.trim();
      }
      const nested = extractTextFromUnknown(candidate);
      if (nested) return nested;
    }
    if (obj.content !== undefined) {
      const contentText = extractTextFromUnknown(obj.content);
      if (contentText) return contentText;
    }
    if (Array.isArray(obj.messages)) {
      const assistantMessages = obj.messages.filter(
        item => item && typeof item === 'object' && (item as any).role === 'assistant',
      );
      for (const message of assistantMessages) {
        const preview = extractTextFromUnknown((message as any).content ?? message);
        if (preview) return preview;
      }
      const fallback = extractTextFromUnknown(obj.messages);
      if (fallback) return fallback;
    }
    for (const value of Object.values(obj)) {
      const result = extractTextFromUnknown(value);
      if (result) return result;
    }
  }
  return null;
}

function coercePreviewText(value: unknown): string | null {
  const text = extractTextFromUnknown(value);
  if (!text) return null;
  return text.length > MAX_PREVIEW_LENGTH ? text.slice(0, MAX_PREVIEW_LENGTH) : text;
}

function normalizePreview(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed);
    const parsedText = coercePreviewText(parsed);
    if (parsedText) return parsedText;
  } catch {
    // ignore parse errors
  }
  return coercePreviewText(trimmed);
}

function previewFromMessages(messages: ChatSessionDetail['messages'] | undefined): string | null {
  if (!messages) return null;
  for (const message of messages) {
    if (message.role === 'assistant') {
      const preview = coercePreviewText(message.content);
      if (preview) return preview;
    }
  }
  return null;
}

export default function WorkspacePage() {
  const { isReady: backendReady, isChecking: backendChecking } = useBackendStatus();
  const [currentView, setCurrentView] = useState<ViewMode>('chat');
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSessionSummary | null>(null);
  const [detail, setDetail] = useState<ChatSessionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gpt-5-mini');
  const [selectedDataSource, setSelectedDataSource] = useState('all');
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [importCSVOpen, setImportCSVOpen] = useState(false);
  const [importParquetOpen, setImportParquetOpen] = useState(false);
  const [importPostgresOpen, setImportPostgresOpen] = useState(false);
  const [importSQLiteOpen, setImportSQLiteOpen] = useState(false);
  const [dataSourcesRefresh, setDataSourcesRefresh] = useState(0);
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

  const updateSessionPreview = useCallback((sessionId: string, preview: string | null | undefined) => {
    if (!preview) return;
    setSessions(prev =>
      prev.map(session => (session.id === sessionId ? { ...session, last_message_preview: preview } : session)),
    );
  }, []);

  const pickActiveRunId = useCallback((session: ChatSessionSummary | null | undefined) => {
    if (!session) return null;
    return session.status === 'active' ? session.run_id ?? null : null;
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      console.info('[Workspace] Loading sessions');
      const data = await fetchChatSessions();
      console.info('[Workspace] Sessions fetched', data);
      const normalizedSessions = data.map(session => ({
        ...session,
        last_message_preview: normalizePreview(session.last_message_preview),
      }));
      setSessions(normalizedSessions);
      setActiveSession(prev => {
        if (normalizedSessions.length === 0) {
          console.info('[Workspace] No sessions found');
          setActiveRunId(null);
          return null;
        }
        if (!prev) {
          console.info('[Workspace] Selecting first session', normalizedSessions[0]);
          setActiveRunId(pickActiveRunId(normalizedSessions[0]));
          return normalizedSessions[0];
        }
        const match = normalizedSessions.find(session => session.id === prev.id);
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

  // Load default model from settings and data sources
  useEffect(() => {
    if (backendReady) {
      void (async () => {
        try {
          const settings = await fetchSettings();
          if (settings.llm_model) {
            setSelectedModel(settings.llm_model);
          }
        } catch (error) {
          console.error('Failed to load default model from settings', error);
        }
        
        try {
          const sources = await fetchDataSources();
          setDataSources(sources);
        } catch (error) {
          console.error('Failed to load data sources', error);
        }
      })();
    }
  }, [backendReady]);

  useEffect(() => {
    if (backendReady) {
      void loadSessions();
    }
  }, [loadSessions, backendReady]);

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
          const detailPreview = previewFromMessages(response.messages);
          if (detailPreview) {
            updateSessionPreview(sessionId, detailPreview);
          }
          const nextRunId = response.status === 'active' ? response.run_id ?? currentSession.run_id ?? null : null;
          setActiveRunId(nextRunId);
          setActiveSession(prev =>
            prev && prev.id === sessionId
              ? {
                  ...prev,
                  run_id: response.run_id ?? prev.run_id,
                  status: response.status,
                  last_message_preview: detailPreview ?? prev.last_message_preview,
                }
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
  }, [activeSession?.id, fetchDetail, isCreatingConversation, updateSessionPreview]);

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
          const detailPreview = previewFromMessages(response.messages);
          if (detailPreview) {
            updateSessionPreview(currentSession.id, detailPreview);
          }
          const nextRunId = response.status === 'active' ? response.run_id ?? activeRunId : null;
          setActiveSession(prev =>
            prev && prev.id === currentSession.id
              ? {
                  ...prev,
                  run_id: response.run_id ?? prev.run_id,
                  status: response.status,
                  last_message_preview: detailPreview ?? prev.last_message_preview,
                }
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
  }, [activeSession, activeRunId, fetchDetail, loadSessions, streamEvents, updateSessionPreview]);

  const handleSelectSession = useCallback(
    (session: ChatSessionSummary) => {
      setCurrentView('chat');
      resetStream();
      setIsCreatingConversation(false);
      setActiveRunId(pickActiveRunId(session));
      if (activeSession?.id === session.id) {
        void (async () => {
          try {
            setLoading(true);
            const response = await fetchDetail(session.id, true);
            setDetail(response);
            const detailPreview = previewFromMessages(response.messages);
            if (detailPreview) {
              updateSessionPreview(session.id, detailPreview);
            }
            const nextRunId = response.status === 'active' ? response.run_id ?? activeSession.run_id ?? null : null;
            setActiveRunId(nextRunId);
            setActiveSession(prev =>
              prev && prev.id === session.id
                ? {
                    ...prev,
                    status: response.status,
                    run_id: response.run_id ?? prev.run_id,
                    last_message_preview: detailPreview ?? prev.last_message_preview,
                  }
                : prev,
            );
          } catch (error) {
            console.error('[Workspace] Failed to refresh session detail', error);
          } finally {
            setLoading(false);
          }
        })();
        return;
      }
      setDetail(null);
      const normalizedSelection: ChatSessionSummary = {
        ...session,
        last_message_preview: normalizePreview(session.last_message_preview),
      };
      setActiveSession(normalizedSelection);
      setActiveRunId(pickActiveRunId(normalizedSelection));
    },
    [activeSession, fetchDetail, pickActiveRunId, resetStream, updateSessionPreview],
  );

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
    setCurrentView('chat');
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
          
          const metadata: Record<string, any> = { model: selectedModel };
          if (selectedDataSource && selectedDataSource !== 'all') {
            metadata.data_source = selectedDataSource;
          }
          
          const response = await createConversation({ 
            question: prompt, 
            model: selectedModel,
            metadata,
          });
          console.info('[Workspace] Conversation created', response);
          const nowIso = new Date().toISOString();
          const newSession: ChatSessionSummary = {
            id: response.conversation_id ?? response.id,
            title: prompt ? prompt.slice(0, 80) : null,
            status: 'active',
            created_at: nowIso,
            updated_at: nowIso,
            last_message_preview: coercePreviewText(prompt),
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
        const response: AppendMessageResponse = await appendMessage(currentSession.id, { role: 'user', content: { text: prompt }, model: selectedModel });
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
                last_message_preview: coercePreviewText(prompt) ?? prev.last_message_preview,
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
    [activeSession, selectedModel, selectedDataSource, loadSessions, resetStream],
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

  const handleImportClick = useCallback((connectorType: string) => {
    switch (connectorType) {
      case 'csv':
        setImportCSVOpen(true);
        break;
      case 'parquet':
        setImportParquetOpen(true);
        break;
      case 'postgres':
        setImportPostgresOpen(true);
        break;
      case 'sqlite':
        setImportSQLiteOpen(true);
        break;
      default:
        console.error('Unknown connector type:', connectorType);
    }
  }, []);

  const handleImportSuccess = useCallback(() => {
    // Trigger refresh of data sources list
    setDataSourcesRefresh(prev => prev + 1);
    // Reload data sources for dropdown
    void (async () => {
      try {
        const sources = await fetchDataSources();
        setDataSources(sources);
      } catch (error) {
        console.error('Failed to reload data sources', error);
      }
    })();
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
    <div className="flex h-screen w-full flex-1 relative">
      {/* Backend status overlay */}
      {!backendReady && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="rounded-lg border bg-card p-8 text-center shadow-lg">
            <Loader />
            <p className="mt-4 text-sm font-medium text-muted-foreground">
              {backendChecking ? 'Connecting to backend...' : 'Backend is starting...'}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Please wait while the backend initializes
            </p>
          </div>
        </div>
      )}

      {/* Sidebar conversation list */}
      <aside className="hidden w-80 border-r border-border bg-muted/20 px-4 py-6 lg:flex lg:flex-col">
        {/* Top action buttons */}
        <div className="mb-4 flex items-center justify-end gap-2">
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-accent"
            onClick={() => void loadSessions()}
            title="Refresh"
          >
            <RefreshCcwIcon className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 text-primary hover:bg-primary/20"
            onClick={handleNewConversation}
            title="New conversation"
          >
            <PlusIcon className="h-4 w-4" />
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto">
          <ConversationList sessions={sessions} activeId={activeSession?.id} onSelect={handleSelectSession} onDelete={handleDeleteSession} />
        </div>

        {/* Bottom buttons */}
        <div className="mt-4 space-y-2">
          <button
            type="button"
            className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-sm transition ${
              currentView === 'data-sources'
                ? 'border-primary/60 bg-primary/10 text-primary'
                : 'border-border bg-card hover:bg-accent'
            }`}
            onClick={() => setCurrentView('data-sources')}
          >
            <DatabaseIcon className="h-4 w-4" />
            <span>Data Sources</span>
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm hover:bg-accent"
            onClick={() => setSettingsOpen(true)}
          >
            <SettingsIcon className="h-4 w-4" />
            <span>Settings</span>
          </button>
        </div>
      </aside>

      {/* Settings Modal */}
      <SettingsModal 
        open={settingsOpen} 
        onOpenChange={setSettingsOpen}
        onSettingsSaved={(model) => setSelectedModel(model)}
      />

      {/* Import Modals */}
      <ImportCSVModal
        open={importCSVOpen}
        onOpenChange={setImportCSVOpen}
        onImportSuccess={handleImportSuccess}
      />
      <ImportParquetModal
        open={importParquetOpen}
        onOpenChange={setImportParquetOpen}
        onImportSuccess={handleImportSuccess}
      />
      <ImportPostgresModal
        open={importPostgresOpen}
        onOpenChange={setImportPostgresOpen}
        onImportSuccess={handleImportSuccess}
      />
      <ImportSQLiteModal
        open={importSQLiteOpen}
        onOpenChange={setImportSQLiteOpen}
        onImportSuccess={handleImportSuccess}
      />

      {/* Main content area - view switching */}
      <div className="relative flex size-full flex-col overflow-hidden bg-muted/5">
      {currentView === 'data-sources' ? (
        <DataSourcesView 
          onImportClick={handleImportClick}
          refreshTrigger={dataSourcesRefresh}
        />
      ) : (
        <Fragment>
        <div className="relative flex size-full flex-col divide-y overflow-hidden">
        <Conversation>
          <ConversationContent className="flex flex-col min-h-full">
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
                <div className="mx-auto max-w-3xl text-center space-y-6">
                  <p className="text-sm text-muted-foreground">
                    {activeSession ? 'No messages yet.' : 'Start a new conversation below.'}
                  </p>
                  {!activeSession && (
                    <Suggestions>
                      {suggestions.map(suggestion => (
                        <Suggestion key={suggestion} onClick={() => handleSuggestionClick(suggestion)} suggestion={suggestion} />
                      ))}
                    </Suggestions>
                  )}
                </div>
              </div>
            )}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        {/* Input area */}
        <div className="shrink-0 pt-4">
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
                  <PromptInputTools>
                    {/* Model selection */}
                    <PromptInputModelSelect value={selectedModel} onValueChange={setSelectedModel}>
                      <PromptInputModelSelectTrigger>
                        <PromptInputModelSelectValue />
                      </PromptInputModelSelectTrigger>
                      <PromptInputModelSelectContent>
                        {MODELS.map(model => (
                          <PromptInputModelSelectItem key={model.id} value={model.id}>
                            {model.name}
                          </PromptInputModelSelectItem>
                        ))}
                      </PromptInputModelSelectContent>
                    </PromptInputModelSelect>
                    
                    {/* Data source selection */}
                    <PromptInputModelSelect value={selectedDataSource} onValueChange={setSelectedDataSource}>
                      <PromptInputModelSelectTrigger>
                        <PromptInputModelSelectValue placeholder="All sources" />
                      </PromptInputModelSelectTrigger>
                      <PromptInputModelSelectContent>
                        <PromptInputModelSelectItem value="all">All sources</PromptInputModelSelectItem>
                        {dataSources.map(source => (
                          <PromptInputModelSelectItem key={source.id} value={source.target_table}>
                            {source.target_table}
                          </PromptInputModelSelectItem>
                        ))}
                      </PromptInputModelSelectContent>
                    </PromptInputModelSelect>
                  </PromptInputTools>
                  <PromptInputSubmit disabled={!input.trim() || isStreaming} status={status} />
                </PromptInputFooter>
              </PromptInput>
            </div>
          </div>
        </div>
      </div>
      </Fragment>
      )}
      </div>
    </div>
  );
}
