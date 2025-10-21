import { getBackendUrl } from './api';

export interface ChatSessionSummary {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_message_preview: string | null;
  run_id?: string;
  events_url?: string;
}

export interface ChatSessionDetail {
  id: string;
  status: string;
  messages: Array<{ id: string; role: string; content: any; created_at: string; seq: number }>;
  events?: Array<{ type: string; subtype: string; content: any; metadata?: any; timestamp?: string }>;
  events_url?: string;
  run_id?: string;
}

export async function fetchChatSessions(): Promise<ChatSessionSummary[]> {
  const response = await fetch(`${getBackendUrl()}/api/v1/chat/sessions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.status}`);
  }
  return response.json();
}

export async function fetchChatSession(conversationId: string, includeEvents = false): Promise<ChatSessionDetail> {
  const response = await fetch(
    `${getBackendUrl()}/api/v1/chat/sessions/${conversationId}${includeEvents ? '?include_events=true' : ''}`,
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch session ${conversationId}: ${response.status}`);
  }
  return response.json();
}

export interface CreateConversationPayload {
  question?: string;
  metadata?: Record<string, unknown>;
  conversation_id?: string;
}

export interface CreateConversationResponse {
  id: string;
  run_id?: string;
  events_url?: string;
  conversation_id?: string;
}

export async function createConversation(payload: CreateConversationPayload): Promise<CreateConversationResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/chat/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to create conversation: ${response.status} ${text}`);
  }
  return response.json();
}

export interface AppendMessageResponse {
  status: string;
  run_id?: string;
  events_url?: string;
  conversation_id?: string;
}

export async function appendMessage(
  conversationId: string,
  payload: { role: string; content: any },
): Promise<AppendMessageResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/chat/sessions/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to append message: ${response.status} ${text}`);
  }
  return response.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetch(`${getBackendUrl()}/api/v1/chat/sessions/${conversationId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to delete conversation ${conversationId}: ${response.status} ${text}`);
  }
}

export interface ChatSettings {
  data_sources?: any;
  dbt_project?: any;
  ui_preferences?: any;
  llm_provider?: any;
}

export async function fetchChatSettings(): Promise<ChatSettings> {
  const response = await fetch(`${getBackendUrl()}/api/v1/chat/settings`);
  if (!response.ok) {
    throw new Error(`Failed to fetch settings: ${response.status}`);
  }
  return response.json();
}

export async function updateChatSettings(payload: ChatSettings): Promise<ChatSettings> {
  const response = await fetch(`${getBackendUrl()}/api/v1/chat/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to update settings: ${response.status} ${text}`);
  }
  return response.json();
}
