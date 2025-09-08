export * from "./chat";
export * from "./prompt";
export * from "./sync";
// Minimal app config and access store implementations used across the page
import { create } from "zustand";
import { createPersistStore } from "../utils/store";
import { StoreKey } from "../constant";

export enum Theme { Auto = "auto", Light = "light", Dark = "dark" }
export enum SubmitKey { Enter = "Enter", CtrlEnter = "CtrlEnter", ShiftEnter = "ShiftEnter", AltEnter = "AltEnter", MetaEnter = "MetaEnter" }

type ModelConfig = {
  model: string;
  max_tokens: number;
  enableInjectSystemPrompts: boolean;
  template: string;
  historyMessageCount: number;
  compressMessageLengthThreshold: number;
  sendMemory: boolean;
  compressModel?: string;
  compressProviderName?: string;
  providerName?: string;
};

type AppConfigState = {
  theme: Theme;
  fontSize: number;
  fontFamily: string;
  tightBorder: boolean;
  sidebarWidth?: number;
  dontShowMaskSplashScreen?: boolean;
  enableAutoGenerateTitle?: boolean;
  disablePromptHint?: boolean;
  sendPreviewBubble?: boolean;
  enableArtifacts?: boolean;
  enableCodeFold?: boolean;
  avatar?: string;
  submitKey: SubmitKey;
  modelConfig: ModelConfig;
  realtimeConfig: { enable: boolean };
  ttsConfig: { enable: boolean; model: string; voice: string; speed: number; engine?: string };
};

export const useAppConfig = createPersistStore<AppConfigState, { update: (updater: (c: AppConfigState) => void) => void }>(
  {
    theme: Theme.Auto,
    fontSize: 14,
    fontFamily: "",
    tightBorder: false,
    sidebarWidth: 320,
    dontShowMaskSplashScreen: true,
    enableAutoGenerateTitle: true,
    disablePromptHint: false,
    sendPreviewBubble: true,
    enableArtifacts: true,
    enableCodeFold: true,
    avatar: "2699-fe0f",
    submitKey: SubmitKey.Enter,
    modelConfig: {
      model: "athena-default",
      max_tokens: 8192,
      enableInjectSystemPrompts: false,
      template: "{{input}}",
      historyMessageCount: 32,
      compressMessageLengthThreshold: 1000,
      sendMemory: false,
      providerName: "Athena",
    },
    realtimeConfig: { enable: false },
    ttsConfig: { enable: false, model: "tts-1", voice: "alloy", speed: 1, engine: "OpenAI-TTS" },
  },
  (set, get) => ({
    update: (updater) => {
      const draft = { ...get() };
      updater(draft);
      set(draft as AppConfigState);
    },
  }),
  { name: StoreKey.Config, version: 1 },
);

type AccessState = {
  disableFastLink: boolean;
  hideBalanceQuery: boolean;
  openaiUrl: string;
  provider: string;
  accessCode?: string;
  openaiApiKey?: string;
  googleApiKey?: string;
  visionModels?: string;
};

export const useAccessStore = create<AppConfigState & AccessState & { update: (updater: (s: any) => void) => void; fetch: () => void; isAuthorized: () => boolean; edgeVoiceName: () => string }>((set, get) => ({
  // Access
  disableFastLink: true,
  hideBalanceQuery: true,
  openaiUrl: "",
  provider: "Athena",
  accessCode: "",
  openaiApiKey: "",
  googleApiKey: "",
  visionModels: "",
  // App config overlay (not persisted here)
  theme: Theme.Auto,
  fontSize: 14,
  fontFamily: "",
  tightBorder: false,
  dontShowMaskSplashScreen: true,
  enableAutoGenerateTitle: true,
  disablePromptHint: false,
  sendPreviewBubble: true,
  enableArtifacts: true,
  enableCodeFold: true,
  avatar: "2699-fe0f",
  submitKey: SubmitKey.Enter,
  modelConfig: useAppConfig.getState().modelConfig,
  realtimeConfig: { enable: false },
  ttsConfig: { enable: false, model: "tts-1", voice: "alloy", speed: 1, engine: "OpenAI-TTS" },
  update: (updater) => set((state) => {
    const draft = { ...state } as any;
    updater(draft);
    return draft;
  }),
  fetch: () => {
    // no-op for Athena new-tab
  },
  isAuthorized: () => true,
  edgeVoiceName: () => "en-US-GuyNeural",
}));

// duplicates removed