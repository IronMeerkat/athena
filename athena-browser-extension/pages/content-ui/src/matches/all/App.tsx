import { useCallback, useState } from 'react';
import BlockModal, { type ChatMessage } from './components/BlockModal';
import { useRuntimeMessage } from './hooks/useRuntimeMessage';
import type { RuntimeMessage } from './types/messages';

export default function App() {
  const [showModal, setShowModal] = useState(false);
  const [pageInfo, setPageInfo] = useState<{ url: string; title: string } | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "This page looks distracting. If you need access, explain why it's necessary for work or your short-term wellbeing.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // No-op window message listener removed

  useRuntimeMessage((message: RuntimeMessage) => {
    if (message.type === 'SHOW_BLOCK_MODAL') {
      setPageInfo({ url: message.payload.url, title: message.payload.title });
      setShowModal(true);
      return;
    }
    if (message.type === 'CLOSE_BLOCK_MODAL') {
      setShowModal(false);
      setMessages([
        {
          role: 'assistant',
          content:
            "This page looks distracting. If you need access, explain why it's necessary for work or your short-term wellbeing.",
        },
      ]);
      setInput('');
    }
  });

  const ask = useCallback(async () => {
    if (!pageInfo || !input.trim()) return;
    const newUserMsg: ChatMessage = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, newUserMsg]);
    setInput('');
    setIsLoading(true);
    try {
      const result = await new Promise<{ assistant: string; allow: boolean; minutes: number }>(resolve => {
        chrome.runtime.sendMessage(
          {
            type: 'EVALUATE_APPEAL',
            payload: { conversation: [...messages, newUserMsg], url: pageInfo.url, title: pageInfo.title },
          },
          resolve,
        );
      });
      setMessages(prev => [...prev, { role: 'assistant', content: result.assistant }]);
      if (result.allow) {
        await new Promise(resolve => {
          chrome.runtime.sendMessage(
            { type: 'APPEAL_ALLOW', payload: { url: pageInfo.url, minutes: result.minutes || 20 } },
            resolve,
          );
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [pageInfo, input, messages]);

  // Enter handling is implemented inside BlockModal input

  return (
    <>
      {showModal ? (
        <BlockModal
          open={true}
          pageInfo={pageInfo}
          messages={messages}
          input={input}
          isLoading={isLoading}
          onInputChange={setInput}
          onSend={ask}
        />
      ) : null}
    </>
  );
}
