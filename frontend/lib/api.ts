import type { DeckDetail, DeckListItem } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export async function listDecks(): Promise<DeckListItem[]> {
  return j(await fetch(`${API_BASE}/api/decks`, { cache: "no-store" }));
}

export async function getDeck(id: string): Promise<DeckDetail> {
  return j(await fetch(`${API_BASE}/api/decks/${id}`, { cache: "no-store" }));
}

export async function uploadDeck(file: File): Promise<{ id: string }> {
  const fd = new FormData();
  fd.append("file", file);
  return j(await fetch(`${API_BASE}/api/decks`, { method: "POST", body: fd }));
}

export async function runDemo(): Promise<{ id: string }> {
  return j(await fetch(`${API_BASE}/api/decks/demo`, { method: "POST" }));
}

export type ExportFormat = "pdf" | "docx" | "html";

export function exportUrl(id: string, format: ExportFormat = "pdf"): string {
  return `${API_BASE}/api/decks/${id}/export?format=${format}`;
}

export async function health(): Promise<{
  mock_mode: boolean;
  llm: boolean;
  search: boolean;
  enrichment: boolean;
}> {
  return j(await fetch(`${API_BASE}/health`, { cache: "no-store" }));
}
