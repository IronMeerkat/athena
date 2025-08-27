import { memo, useEffect, useMemo, useRef } from 'react';

export type ChatMessage = { role: 'user' | 'assistant'; content: string };

type BlockModalProps = {
  open: boolean;
  pageInfo: { url: string; title: string } | null;
  messages: ChatMessage[];
  input: string;
  isLoading: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
};

const BlockModal = memo(function BlockModal({
  open,
  pageInfo,
  messages,
  input,
  isLoading,
  onInputChange,
  onSend,
}: BlockModalProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const labelId = useMemo(() => 'spai-dialog-title', []);
  const descId = useMemo(() => 'spai-dialog-desc', []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
      }
    };
    window.addEventListener('keydown', onKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', onKeyDown, { capture: true });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    // Lock background scroll while modal is open
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverscroll = getComputedStyle(document.documentElement).getPropertyValue('overscroll-behavior');
    const previousBodyOverscroll = getComputedStyle(document.body).getPropertyValue('overscroll-behavior');
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    document.documentElement.style.setProperty('overscroll-behavior', 'none');
    document.body.style.setProperty('overscroll-behavior', 'none');
    return () => {
      document.documentElement.style.overflow = previousHtmlOverflow;
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.setProperty('overscroll-behavior', previousHtmlOverscroll || 'auto');
      document.body.style.setProperty('overscroll-behavior', previousBodyOverscroll || 'auto');
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    // Autofocus the input when opened
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    // Trap focus within the modal content
    const handleFocusIn = (e: FocusEvent) => {
      const wrapper = wrapperRef.current;
      if (!wrapper) return;
      if (e.target instanceof Node && !wrapper.contains(e.target)) {
        e.stopPropagation();
        // Redirect focus to input or wrapper
        (inputRef.current ?? wrapper).focus();
      }
    };
    document.addEventListener('focusin', handleFocusIn, true);
    return () => document.removeEventListener('focusin', handleFocusIn, true);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[2147483647] flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" aria-hidden="true" />
      <div
        className="relative z-10 flex h-[min(90vw,90vh)] w-[min(90vw,90vh)] max-w-none origin-center flex-col rounded-2xl border border-slate-200 bg-white/95 text-base shadow-2xl ring-1 ring-black/5"
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelId}
        aria-describedby={descId}
        tabIndex={-1}
        ref={wrapperRef}>
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-medium uppercase tracking-wide text-slate-500">Stay Productive</div>
            <div id={labelId} className="truncate text-xl font-semibold text-slate-900">
              Focus Coach
            </div>
            {pageInfo && (
              <div id={descId} className="mt-1 truncate text-sm text-slate-500" title={pageInfo.url}>
                {pageInfo.title}
              </div>
            )}
          </div>
        </div>
        <div className="flex-1 overflow-auto px-4 py-3">
          <div className="space-y-2">
            {messages.map((m, idx) => (
              <div key={idx} className="flex">
                <div
                  className={
                    m.role === 'assistant'
                      ? 'max-w-[80%] rounded-xl bg-slate-100 px-3 py-2 text-slate-800'
                      : 'ml-auto max-w-[80%] rounded-xl bg-blue-600 px-3 py-2 text-white'
                  }>
                  <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">{m.role}</div>
                  <div className="text-base leading-relaxed">{m.content}</div>
                </div>
              </div>
            ))}
            {isLoading && <div className="text-base text-slate-500">Thinking…</div>}
          </div>
        </div>
        <div className="border-t border-slate-100 px-4 py-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => onInputChange(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  onSend();
                } else if (e.key === 'Escape') {
                  // Block escape in the input as well
                  e.preventDefault();
                  e.stopPropagation();
                }
              }}
              placeholder="Explain why you need this site right now…"
              className="flex-1 rounded-lg border border-slate-300 px-4 py-3 text-base shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
              ref={inputRef}
            />
            <button
              onClick={onSend}
              disabled={isLoading || !input.trim()}
              className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-3 text-base font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50">
              Send
            </button>
          </div>
          <div className="mt-2 text-sm text-slate-500">
            If granted, the domain will be whitelisted temporarily (default 20 minutes).
          </div>
        </div>
      </div>
    </div>
  );
});

export default BlockModal;
