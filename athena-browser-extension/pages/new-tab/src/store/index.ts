export * from "./chat";
export * from "./prompt";
export * from "./sync";
// Minimal app config and access store shims to satisfy imports
export const useAppConfig: any = { getState: () => ({
  theme: "auto",
  fontSize: 14,
  fontFamily: "",
  tightBorder: false,
  modelConfig: {
    model: "athena-default",
    max_tokens: 8192,
    enableInjectSystemPrompts: false,
    template: "{{input}}",
    historyMessageCount: 32,
    compressMessageLengthThreshold: 1000,
    sendMemory: false,
  },
  realtimeConfig: { enable: false },
  ttsConfig: { enable: false, model: "tts-1", voice: "alloy", speed: 1 },
  update: (_: any) => {},
}), update: (_: any) => {} };

export const useAccessStore: any = { getState: () => ({
  isAuthorized: () => true,
  disableFastLink: true,
  hideBalanceQuery: true,
  openaiUrl: "",
  provider: "Athena",
  update: (_: any) => {},
  fetch: () => {},
  edgeVoiceName: () => "en-US-GuyNeural",
}) };

export enum Theme { Auto = "auto", Light = "light", Dark = "dark" }
export enum SubmitKey { Enter = "Enter", CtrlEnter = "CtrlEnter", ShiftEnter = "ShiftEnter", AltEnter = "AltEnter", MetaEnter = "MetaEnter" }