export interface AgentRunResponse {
  run_id: string;
  events_url: string;
}

const DEFAULT_BACKEND_URL = '';

export function getBackendUrl(): string {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  return base && base.length > 0 ? base.replace(/\/$/, '') : DEFAULT_BACKEND_URL;
}

export async function fetchBackendHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch(`${getBackendUrl()}/health`, { method: 'GET', signal });
    return response.ok;
  } catch (error) {
    console.error('Health check failed', error);
    return false;
  }
}

export async function startAgentRun(question: string, signal?: AbortSignal): Promise<AgentRunResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/agent/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to start agent run: ${response.status} ${errorBody}`);
  }

  return (await response.json()) as AgentRunResponse;
}
