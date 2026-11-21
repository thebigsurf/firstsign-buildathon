import { api } from "../api";
import type { InboxMessage } from "../types";

export interface Sample {
  id: string;
  label: string;
  kind: "audio" | "image";
  chemistId: string;
  media: string;
  url: string;
}

export const baseName = (path: string): string => path.split("/").pop() ?? path;

/** Bundled sample orders from the demo inbox: up to 3 voice notes and 2 photos, each with the chemist who "sent" it. */
export function pickSamples(messages: InboxMessage[], chemistName: (id: string) => string): Sample[] {
  const out: Sample[] = [];
  let v = 0;
  let p = 0;
  for (const m of messages) {
    const url = api.mediaUrl(m);
    if (!url || !m.media) continue;
    if (m.type === "voice" && v < 3) {
      v += 1;
      out.push({ id: m.id, label: `Voice note ${v}, ${chemistName(m.chemist_id)}`, kind: "audio", chemistId: m.chemist_id, media: m.media, url });
    } else if (m.type === "photo" && p < 2) {
      p += 1;
      out.push({ id: m.id, label: `Photo of list ${p}, ${chemistName(m.chemist_id)}`, kind: "image", chemistId: m.chemist_id, media: m.media, url });
    }
  }
  return out;
}
