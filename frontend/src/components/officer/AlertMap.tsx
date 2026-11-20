import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useMemo, useState } from "react";
import { Circle, MapContainer, Marker, TileLayer, Tooltip } from "react-leaflet";
import { LEVEL_RANK, ratioText } from "../../lib/format";
import { useRefData } from "../../lib/refdata";
import type { Cell, Group, Level, Pincode } from "../../types";
import { levelWord } from "../ui/Badge";

const RADIUS: Record<Level, number> = { normal: 350, watch: 600, alert: 900 };
const FILL: Record<Level, number> = { normal: 0.12, watch: 0.25, alert: 0.35 };
const WEIGHT: Record<Level, number> = { normal: 1, watch: 2, alert: 3 };
const COLOR: Record<Level, string> = { normal: "var(--map-normal)", watch: "var(--map-watch)", alert: "var(--map-alert)" };

export interface PinState {
  pin: Pincode;
  cell: Cell | null;
  level: Level;
}

/** For each pin code: the cell for the chosen group, or the highest-level, highest-ratio cell across groups. */
export function pinStates(pincodes: Pincode[], cells: Cell[], group: string): PinState[] {
  return pincodes.map((pin) => {
    const mine = cells.filter((c) => c.pin === pin.pin && (group === "all" || c.group === group));
    const best = [...mine].sort((a, b) => LEVEL_RANK[b.level] - LEVEL_RANK[a.level] || b.ratio - a.ratio)[0] ?? null;
    return { pin, cell: best, level: best?.level ?? "normal" };
  });
}

function labelIcon(pin: string): L.DivIcon {
  return L.divIcon({ className: "", html: `<span class="fs-pin-label">${pin}</span>`, iconSize: [48, 14], iconAnchor: [24, -6] });
}

interface Props {
  pincodes: Pincode[];
  cells: Cell[];
  group: string;
  groups: Group[];
  selectedPin: string | null;
  pulsePins: Set<string>;
  onSelectPin: (pin: string) => void;
  onGroupChange: (group: string) => void;
  className?: string;
}

function Legend() {
  const swatch = (level: Level): JSX.Element => (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
      <circle
        cx="11"
        cy="11"
        r={level === "alert" ? 9 : level === "watch" ? 8 : 6}
        fill={COLOR[level]}
        fillOpacity={FILL[level]}
        stroke={COLOR[level]}
        strokeWidth={WEIGHT[level]}
        strokeDasharray={level === "watch" ? "4 3" : undefined}
      />
    </svg>
  );
  return (
    <div className="absolute bottom-3 left-3 z-[1000] max-w-[14rem] rounded-lg border border-border bg-surface p-3 text-sm text-text shadow-2">
      <p className="label-xs m-0 mb-1">Level</p>
      <ul className="m-0 list-none space-y-1 p-0">
        {(["normal", "watch", "alert"] as Level[]).map((l) => (
          <li key={l} className="flex items-center gap-2">
            {swatch(l)} {levelWord(l)}
          </li>
        ))}
      </ul>
      <p className="m-0 mt-2 text-xs text-muted">Circle size = how far above normal. Simulated history for demo.</p>
    </div>
  );
}

export default function AlertMap({ pincodes, cells, group, groups, selectedPin, pulsePins, onSelectPin, onGroupChange, className }: Props) {
  const { groupLabel } = useRefData();
  const [tileErrors, setTileErrors] = useState(0);
  const [tilesLoaded, setTilesLoaded] = useState(false);
  const tilesFailed = tileErrors >= 4 && !tilesLoaded;

  const states = useMemo(() => pinStates(pincodes, cells, group), [pincodes, cells, group]);
  const bounds = useMemo(() => pincodes.map((p): [number, number] => [p.lat, p.lng]), [pincodes]);
  const icons = useMemo(() => new Map(pincodes.map((p) => [p.pin, labelIcon(p.pin)])), [pincodes]);

  const describe = (s: PinState): string =>
    s.cell
      ? `${s.pin.area} ${s.pin.pin}: ${groupLabel(s.cell.group)} ${ratioText(s.cell.ratio)} normal, ${levelWord(s.level)}`
      : `${s.pin.area} ${s.pin.pin}: Normal`;

  return (
    <div
      role="application"
      aria-label="Map of illness signals by pin code. The same information is in the alert list next to it."
      className={`relative overflow-hidden rounded-lg border border-border ${className ?? ""}`}
    >
      <div className="absolute right-3 top-3 z-[1000] rounded-lg border border-border bg-surface p-2 shadow-2">
        <label className="flex items-center gap-2 text-sm font-medium text-text">
          Group
          <select className="input min-h-9 w-auto py-0" value={group} onChange={(e) => onGroupChange(e.target.value)}>
            <option value="all">All groups</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {bounds.length > 0 && (
        <MapContainer bounds={bounds} boundsOptions={{ padding: [32, 32] }} scrollWheelZoom className="h-full w-full" style={{ minHeight: 280 }}>
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            eventHandlers={{
              tileerror: () => setTileErrors((n) => n + 1),
              tileload: () => setTilesLoaded(true),
            }}
          />
          {!tilesFailed &&
            states.map((s) => {
              const pulsing = pulsePins.has(s.pin.pin);
              const selected = selectedPin === s.pin.pin;
              return (
                <Circle
                  key={`${s.pin.pin}-${pulsing ? "p" : "s"}`}
                  center={[s.pin.lat, s.pin.lng]}
                  radius={RADIUS[s.level]}
                  pathOptions={{
                    color: COLOR[s.level],
                    fillColor: COLOR[s.level],
                    fillOpacity: FILL[s.level],
                    weight: WEIGHT[s.level] + (selected ? 2 : 0),
                    dashArray: s.level === "watch" ? "6 4" : undefined,
                    className: pulsing ? "fs-pulse" : undefined,
                  }}
                  eventHandlers={{ click: () => onSelectPin(s.pin.pin) }}
                >
                  <Tooltip sticky>{describe(s)}</Tooltip>
                </Circle>
              );
            })}
          {!tilesFailed &&
            states
              .filter((s) => s.level !== "normal")
              .map((s) => <Marker key={`l-${s.pin.pin}`} position={[s.pin.lat, s.pin.lng]} icon={icons.get(s.pin.pin)!} interactive={false} keyboard={false} />)}
        </MapContainer>
      )}

      {tilesFailed && (
        <div role="status" className="absolute inset-x-3 top-14 z-[1000] rounded-md border border-watch bg-watchBg p-3 text-sm font-medium text-watch">
          Map tiles did not load. The list still works.
        </div>
      )}

      <Legend />

      <ul className="sr-only">
        {states.map((s) => (
          <li key={s.pin.pin}>
            <button type="button" onClick={() => onSelectPin(s.pin.pin)}>
              {s.pin.area} {s.pin.pin}, {levelWord(s.level).toLowerCase()}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
