// Deprecated: LLM providers removed. Use services/athena.ts that talks to Aegis.
export type AppealTurn = { role: 'user' | 'assistant'; content: string };
export type AppealDecision = { assistant: string; allow: boolean; minutes: number };
export const isDistraction = (_title: string): any => false;
export const evaluateAppeal = (
  _conversation: AppealTurn[],
  _context: { url: string; title: string },
): any => ({ assistant: 'Not available', allow: false, minutes: 0 });
