import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: process.env.CEB_OPENAI_API_KEY,
});

export const isDistraction = async (title: string): Promise<boolean> => {
  const response = await client.chat.completions.create({
    model: 'gpt-5-nano',
    messages: [
      {
        role: 'system',
        content:
          'You are a very strict focus guardian to a software engineer. Allow tech-related subreddits and youtube videos, block all other social media sites. Allow tech-related websites and articles, block everything else. Return ONLY a strict JSON object: {"distraction": boolean}. No prose.',
      },
      { role: 'user', content: `Title: ${title}` },
    ],
  });

  console.log(response);
  const content = response.choices[0]?.message?.content ?? '{}';
  try {
    const data = JSON.parse(content as string) as { distraction?: boolean };
    return Boolean(data.distraction);
  } catch {
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
  const response = await client.chat.completions.create({
    model: 'gpt-5-mini',
    messages: [
      {
        role: 'system',
        content:
          'You are a helpful but strict productivity coach. The user is blocked from a potentially distracting site. Engage briefly and decide whether access is justified for work or generalwellbeing. Respond ONLY with strict JSON of the form {"assistant": string, "allow": boolean, "minutes": number}. Keep assistant concise. Minutes should be between 5 and 30 when allow=true, else 0.',
      },
      { role: 'system', content: `Context URL: ${context.url} | Title: ${context.title}` },
      ...conversation,
    ],
  });
  const content =
    (response.choices[0]?.message?.content as string | undefined) ??
    '{"assistant":"Sorry, I could not process that.","allow":false,"minutes":0}';
  try {
    const parsed = JSON.parse(content as string) as AppealDecision;
    console.log(parsed);
    return {
      assistant: parsed.assistant ?? 'I did not understand. Could you rephrase?',
      allow: Boolean(parsed.allow),
      minutes: Math.max(0, Math.min(30, Number(parsed.minutes) || 0)),
    };
  } catch {
    return { assistant: 'I could not process that. Please try again.', allow: false, minutes: 0 };
  }
};
