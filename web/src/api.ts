import type { OpsRun, RunListItem } from "./types";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function fetchLatestRun(): Promise<OpsRun | null> {
  const runs = await getJson<RunListItem[]>("/ops/runs?limit=1");
  if (runs.length === 0) {
    return null;
  }
  return getJson<OpsRun>(`/ops/runs/${runs[0].id}`);
}
