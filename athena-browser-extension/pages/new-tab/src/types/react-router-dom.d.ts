declare module "react-router-dom" {
  import * as React from "react";
  export const HashRouter: React.FC<{ children?: React.ReactNode }>;
  export const Route: React.FC<{ path: string; element: React.ReactNode }>;
  export const Routes: React.FC<{ children?: React.ReactNode }>;
  export const Link: React.FC<{
    to: string;
    state?: unknown;
    className?: string;
    children?: React.ReactNode;
  }>;
  export function useLocation(): { pathname: string };
  export function useNavigate(): (to: string, options?: { state?: unknown }) => void;
}

