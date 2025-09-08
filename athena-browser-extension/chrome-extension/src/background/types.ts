export type AgentContext = {
  tabId?: number;
  env: 'development' | 'production';
};

export type AgentInvokeRequest = {
  type: 'agent:invoke';
  payload: { agent: string; input: unknown };
};

export interface Agent<ResultType = unknown, InputType = unknown> {
  name: string;
  description: string;
  canHandle(input: InputType): boolean;
  run(input: InputType, ctx: AgentContext): Promise<ResultType>;
}

export type AgentResult = {
  ok: boolean;
  agent: string;
  result?: unknown;
  error?: string;
};


