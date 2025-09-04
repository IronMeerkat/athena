const BASE_URL = (process.env.ATHENA_DRF_URL || 'http://192.168.0.248:8000') + '/api';

export const isDistraction = async (title: string): Promise<boolean> => {
  try {
    const res = await fetch(`${BASE_URL}/runs/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ agent_id: 'distraction_guardian', input: { title }, options: { sensitive: false } }),
    });
    if (!res.ok) {
      console.error('Athena-DRF isDistraction failed:', res.status, await res.text());
      return false;
    }
    // We only queue a run here. For now, conservatively do not block immediately.
    // Future: subscribe to /api/runs/<run_id>/events and derive decision.
    const data = (await res.json()) as { run_id?: string };
    if (!data?.run_id) {
      console.warn('Athena-DRF isDistraction: run_id missing in response');
    }
    return false;
  } catch (err) {
    console.error('Athena-DRF isDistraction error:', err);
    return false;
  }
};

export type AppealTurn = { role: 'user' | 'assistant'; content: string };

export type AppealDecision = {
  assistant: string;
  allow: boolean;
  minutes: number;
};

export const evaluateAppeal = async (
  conversation: AppealTurn[],
  context: { url: string; title: string },
): Promise<AppealDecision> => {
  try {
    const res = await fetch(`${BASE_URL}/runs/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ agent_id: 'appeals_agent', input: { conversation, context }, options: { sensitive: false } }),
    });
    if (!res.ok) {
      console.error('Athena-DRF evaluateAppeal failed:', res.status, await res.text());
      return { assistant: 'Unable to evaluate appeal at the moment.', allow: false, minutes: 0 };
    }
    const data = (await res.json()) as { run_id?: string };
    if (!data?.run_id) {
      console.warn('Athena-DRF evaluateAppeal: run_id missing in response');
    }
    // For now, default to deny until the SSE pipeline is wired up in the UI.
    return { assistant: 'Your request is being processed by Athena.', allow: false, minutes: 0 };
  } catch (err) {
    console.error('Athena-DRF evaluateAppeal error:', err);
    return { assistant: 'Error evaluating appeal.', allow: false, minutes: 0 };
  }
};


