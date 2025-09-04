import en from "./en";
export type LocaleType = typeof en;
export const AllLangs = ["en"] as const;
export const ALL_LANG_OPTIONS = { en: "English" } as const;
export function changeLang(_l: string) {}
export function getLang(): string { return "en"; }
export default en;

