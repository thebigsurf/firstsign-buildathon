import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import type { Asha, CatalogueItem, Chemist, Distributor, Group, Health, Pincode } from "../types";

interface RefData {
  loading: boolean;
  catalogue: CatalogueItem[];
  groups: Group[];
  pincodes: Pincode[];
  chemists: Chemist[];
  ashas: Asha[];
  distributor: Distributor | null;
  health: Health | null;
  chemistById: (id: string) => Chemist | undefined;
  pinByCode: (pin: string) => Pincode | undefined;
  groupById: (id: string) => Group | undefined;
  groupLabel: (id: string) => string;
  areaOf: (pin: string) => string;
  reload: () => void;
}

const Ctx = createContext<RefData | null>(null);

export function useRefData(): RefData {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRefData must be used inside <RefDataProvider>");
  return ctx;
}

/** Reference data that rarely changes (catalogue, groups, pin codes, chemists). Loaded once; each part fails on its own. */
export function RefDataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<Omit<RefData, "chemistById" | "pinByCode" | "groupById" | "groupLabel" | "areaOf" | "reload">>({
    loading: true,
    catalogue: [],
    groups: [],
    pincodes: [],
    chemists: [],
    ashas: [],
    distributor: null,
    health: null,
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    const s = ctrl.signal;
    void Promise.allSettled([
      api.catalogue(s),
      api.groups(s),
      api.pincodes(s),
      api.chemists(s),
      api.ashas(s),
      api.distributor(s),
      api.health(s),
    ]).then(([cat, grp, pin, chem, asha, dist, health]) => {
      if (s.aborted) return;
      setState({
        loading: false,
        catalogue: cat.status === "fulfilled" ? cat.value : [],
        groups: grp.status === "fulfilled" ? grp.value : [],
        pincodes: pin.status === "fulfilled" ? pin.value : [],
        chemists: chem.status === "fulfilled" ? chem.value : [],
        ashas: asha.status === "fulfilled" ? asha.value : [],
        distributor: dist.status === "fulfilled" ? dist.value : null,
        health: health.status === "fulfilled" ? health.value : null,
      });
    });
    return () => ctrl.abort();
  }, [tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  const value = useMemo<RefData>(() => {
    const chemMap = new Map(state.chemists.map((c) => [c.chemist_id, c]));
    const pinMap = new Map(state.pincodes.map((p) => [p.pin, p]));
    const groupMap = new Map(state.groups.map((g) => [g.id, g]));
    return {
      ...state,
      chemistById: (id) => chemMap.get(id),
      pinByCode: (pin) => pinMap.get(pin),
      groupById: (id) => groupMap.get(id),
      groupLabel: (id) => groupMap.get(id)?.label ?? id.replace(/_/g, " "),
      areaOf: (pin) => pinMap.get(pin)?.area ?? pin,
      reload,
    };
  }, [state, reload]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
