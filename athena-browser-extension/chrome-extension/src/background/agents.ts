import { Agent, AgentContext } from './types';

export class EchoAgent implements Agent<{ echo: unknown }, unknown> {
  name = 'echo';
  description = 'Echoes back the provided input.';
  canHandle(_input: unknown): boolean {
    return true;
  }
  async run(input: unknown, _ctx: AgentContext): Promise<{ echo: unknown }> {
    return { echo: input };
  }
}

export class SummarizeTitleAgent implements Agent<{ summary: string }, { title?: string }> {
  name = 'summarizeTitle';
  description = 'Summarizes a page title into a short phrase.';
  canHandle(input: { title?: string }): boolean {
    return Boolean(input && typeof input === 'object');
  }
  async run(input: { title?: string }, _ctx: AgentContext): Promise<{ summary: string }> {
    const title = input?.title ?? '';
    const summary = title.length > 60 ? `${title.slice(0, 57)}...` : title;
    return { summary };
  }
}


