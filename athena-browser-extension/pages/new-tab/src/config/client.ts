export function getClientConfig(): { isApp?: boolean; buildMode?: string } | undefined {
  return { isApp: false, buildMode: "web" };
}

