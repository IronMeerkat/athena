import { Agent, AgentContext, AgentInvokeRequest, AgentResult } from './types';

class AgentRegistry {
  private readonly nameToAgent: Map<string, Agent> = new Map();

  register(agent: Agent): void {
    this.nameToAgent.set(agent.name, agent);
  }

  get(name: string): Agent | undefined {
    return this.nameToAgent.get(name);
  }

  list(): Agent[] {
    return [...this.nameToAgent.values()];
  }
}

const registry = new AgentRegistry();

export const getRegistry = (): AgentRegistry => registry;

export async function handleMessage(
  message: AgentInvokeRequest,
  ctx: AgentContext,
): Promise<AgentResult | null> {
  try {
    if (!message || message.type !== 'agent:invoke') return null;
    const { agent: agentName, input } = message.payload;
    const agent = registry.get(agentName);
    if (!agent) {
      return { ok: false, agent: agentName, error: `Agent not found: ${agentName}` };
    }
    if (!agent.canHandle(input)) {
      return { ok: false, agent: agentName, error: 'Input not supported by agent' };
    }
    const result = await agent.run(input, ctx);
    return { ok: true, agent: agentName, result };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('handleMessage error:', msg);
    return { ok: false, agent: (message?.payload as { agent?: string })?.agent ?? 'unknown', error: msg };
  }
}


