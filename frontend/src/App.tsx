import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { Skeleton } from "./components/ui/States";
import { ToastProvider } from "./components/ui/Toast";
import { RefDataProvider } from "./lib/refdata";
import { About } from "./pages/About";
import { Landing } from "./pages/Landing";
import { NotFoundPage } from "./pages/NotFoundPage";

// Leaflet is heavy, so the officer screens load only when someone opens them.
const Officer = lazy(() => import("./pages/Officer").then((m) => ({ default: m.Officer })));
const AlertDetail = lazy(() => import("./pages/AlertDetail").then((m) => ({ default: m.AlertDetail })));
const Inbox = lazy(() => import("./pages/Inbox").then((m) => ({ default: m.Inbox })));
const Radar = lazy(() => import("./pages/Radar").then((m) => ({ default: m.Radar })));
const AshaFlow = lazy(() => import("./pages/Asha").then((m) => ({ default: m.AshaFlow })));

function PageFallback() {
  return (
    <div aria-busy="true" className="mx-auto max-w-[1440px] space-y-4 p-6">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export function App() {
  return (
    <RefDataProvider>
      <ToastProvider>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route element={<Shell />}>
              <Route path="/" element={<Landing />} />
              <Route path="/distributor" element={<Inbox />} />
              <Route path="/distributor/inbox" element={<Inbox />} />
              <Route path="/distributor/radar" element={<Radar />} />
              <Route path="/officer" element={<Officer />} />
              <Route path="/officer/alert/:id" element={<AlertDetail />} />
              <Route path="/asha" element={<AshaFlow />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </Suspense>
      </ToastProvider>
    </RefDataProvider>
  );
}
