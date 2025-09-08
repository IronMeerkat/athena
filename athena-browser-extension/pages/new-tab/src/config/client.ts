export function getClientConfig(): { isApp?: boolean; buildMode?: string } | undefined {
  return { isApp: true, buildMode: "web" };
}

