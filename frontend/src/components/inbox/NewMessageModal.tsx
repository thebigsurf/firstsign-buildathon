import { FileUp, Keyboard, Mic } from "lucide-react";
import { useCallback, useId, useMemo, useState } from "react";
import { cx } from "../../lib/format";
import { useRefData } from "../../lib/refdata";
import type { MessageType } from "../../types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { Recorder, type RecordedAudio } from "../ui/Recorder";

export interface NewMessage {
  chemistId: string;
  type: MessageType;
  blob?: Blob;
  fileName?: string;
  text?: string;
}

type Mode = "record" | "upload" | "type";

const MODES: Array<[Mode, string, typeof Mic]> = [
  ["record", "Record a voice note", Mic],
  ["upload", "Upload a file", FileUp],
  ["type", "Type a message", Keyboard],
];

interface Props {
  open: boolean;
  onClose: () => void;
  onCreate: (m: NewMessage) => void;
}

export function NewMessageModal({ open, onClose, onCreate }: Props) {
  const { chemists, distributor } = useRefData();
  const options = useMemo(() => {
    const ids = distributor?.chemist_ids ?? [];
    const mine = chemists.filter((c) => ids.includes(c.chemist_id));
    return mine.length > 0 ? mine : chemists;
  }, [chemists, distributor]);

  const [chemistId, setChemistId] = useState("");
  const [mode, setMode] = useState<Mode>("record");
  const [audio, setAudio] = useState<RecordedAudio | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const chemistField = useId();
  const textField = useId();
  const fileField = useId();

  const effectiveChemist = chemistId || options[0]?.chemist_id || "";
  const onRecorded = useCallback((a: RecordedAudio | null) => setAudio(a), []);

  const ready =
    Boolean(effectiveChemist) && (mode === "record" ? audio !== null : mode === "upload" ? file !== null : text.trim().length > 0);

  const submit = (): void => {
    if (!ready) return;
    if (mode === "record" && audio) {
      onCreate({ chemistId: effectiveChemist, type: "voice", blob: audio.blob, fileName: audio.fileName });
    } else if (mode === "upload" && file) {
      onCreate({ chemistId: effectiveChemist, type: file.type.startsWith("image/") ? "photo" : "voice", blob: file, fileName: file.name });
    } else {
      onCreate({ chemistId: effectiveChemist, type: "text", text: text.trim() });
    }
    setAudio(null);
    setFile(null);
    setText("");
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New message from a chemist" width="max-w-xl">
      <div className="space-y-5">
        <div>
          <label htmlFor={chemistField} className="mb-1 block text-sm font-medium">
            Which chemist sent it?
          </label>
          <select id={chemistField} className="input" value={effectiveChemist} onChange={(e) => setChemistId(e.target.value)}>
            {options.map((c) => (
              <option key={c.chemist_id} value={c.chemist_id}>
                {c.shop_name} ({c.pin})
              </option>
            ))}
          </select>
        </div>

        <div role="radiogroup" aria-label="How do you want to add it?" className="flex flex-wrap gap-2">
          {MODES.map(([id, label, Icon]) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={mode === id}
              onClick={() => setMode(id)}
              className={cx(
                "inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium",
                mode === id ? "bg-accent text-accentFg" : "border border-borderStrong bg-surface hover:bg-sunken",
              )}
            >
              <Icon size={16} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>

        {mode === "record" && (
          <Recorder
            maxSeconds={60}
            startLabel={<span className="text-sm text-muted">Tap to start. Speak the order the way a chemist would.</span>}
            stopLabel={<span className="text-sm text-muted">Tap to stop</span>}
            recordingLabel="Recording"
            againLabel="Record again"
            deniedMessage={<p className="m-0 text-sm">The microphone is blocked. Allow it in the browser settings, or upload a file instead.</p>}
            unsupportedMessage={<p className="m-0 text-sm">This browser cannot record audio. Upload a file or type the message instead.</p>}
            onRecorded={onRecorded}
          />
        )}
        {mode === "upload" && (
          <div>
            <label htmlFor={fileField} className="mb-1 block text-sm font-medium">
              Voice note or photo of a handwritten list
            </label>
            <input
              id={fileField}
              type="file"
              accept="audio/*,image/*"
              className="input py-2"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file && <p className="mt-1 text-sm text-muted">{file.name}</p>}
          </div>
        )}
        {mode === "type" && (
          <div>
            <label htmlFor={textField} className="mb-1 block text-sm font-medium">
              Message text
            </label>
            <textarea
              id={textField}
              rows={4}
              className="input py-2"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="For example: 10 strip dolo 650, 5 ors, ek cetrizine"
            />
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!ready}>
            Read with Gemini
          </Button>
        </div>
      </div>
    </Modal>
  );
}
