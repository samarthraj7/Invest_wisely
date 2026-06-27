import type { DeckDetail, DeckListItem, IcebreakerSet } from "./types";

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

export interface PitchExtras {
  transcriptText?: string;
  transcriptFile?: File | null;
  video?: File | null;
}

export async function uploadDeck(file: File, extras: PitchExtras = {}): Promise<{ id: string }> {
  const fd = new FormData();
  fd.append("file", file);
  if (extras.transcriptText && extras.transcriptText.trim())
    fd.append("transcript_text", extras.transcriptText.trim());
  if (extras.transcriptFile) fd.append("transcript", extras.transcriptFile);
  if (extras.video) fd.append("video", extras.video);
  return j(await fetch(`${API_BASE}/api/decks`, { method: "POST", body: fd }));
}

export async function runDemo(): Promise<{ id: string }> {
  return j(await fetch(`${API_BASE}/api/decks/demo`, { method: "POST" }));
}

export async function deleteDeck(id: string): Promise<{ ok: boolean }> {
  return j(await fetch(`${API_BASE}/api/decks/${id}`, { method: "DELETE" }));
}

export async function findIcebreakers(id: string, background: string): Promise<IcebreakerSet> {
  return j(
    await fetch(`${API_BASE}/api/decks/${id}/icebreakers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ background }),
    })
  );
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
