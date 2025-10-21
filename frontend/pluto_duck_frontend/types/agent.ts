export type AgentEventType = 'reasoning' | 'tool' | 'message' | 'run';

export type AgentEventSubtype = 'start' | 'chunk' | 'end' | 'final' | 'error';

export interface AgentEvent {
  type: AgentEventType;
  subtype: AgentEventSubtype;
  content: unknown;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export type AgentConversationEvent = AgentEvent & {
  type: 'reasoning' | 'message';
};

export type AgentToolEvent = AgentEvent & {
  type: 'tool';
};

export type AgentRunEvent = AgentEvent & {
  type: 'run';
};

export type AgentEventAny = AgentConversationEvent | AgentToolEvent | AgentRunEvent;
