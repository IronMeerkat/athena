type Controller = { abort: () => void };

const sessionToMessageIdToController: Record<string, Record<string, Controller>> = {};

export const ChatControllerPool = {
  addController(sessionId: string, messageId: string | number, controller: Controller) {
    const sid = String(sessionId);
    const mid = String(messageId);
    sessionToMessageIdToController[sid] = sessionToMessageIdToController[sid] || {};
    sessionToMessageIdToController[sid][mid] = controller;
  },
  stop(sessionId: string, messageId: string | number) {
    const sid = String(sessionId);
    const mid = String(messageId);
    sessionToMessageIdToController[sid]?.[mid]?.abort?.();
  },
  stopAll() {
    Object.values(sessionToMessageIdToController).forEach((m) =>
      Object.values(m).forEach((c) => c.abort?.()),
    );
  },
  remove(sessionId: string, messageId: string | number) {
    const sid = String(sessionId);
    const mid = String(messageId);
    if (sessionToMessageIdToController[sid]) {
      delete sessionToMessageIdToController[sid][mid];
    }
  },
  hasPending() {
    return Object.values(sessionToMessageIdToController).some((m) =>
      Object.keys(m).length > 0,
    );
  },
};

