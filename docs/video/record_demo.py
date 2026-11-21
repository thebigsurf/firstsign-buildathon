"""Records the FirstSign demo walkthrough, one Playwright video per scene.

Run the app first (backend serving frontend/dist) and warm the cache:  python -m app.warm
Usage:  python record_demo.py [base_url] [scene_id ...]
Output: docs/video/raw/<scene_id>.webm  and  raw/timing.json (seconds of video to trim at the start, and length).
Live Gemini is not called during recording unless a result is not cached; all demo content is warmed first.
"""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

D = Path(__file__).parent
RAW = D / "raw"; RAW.mkdir(exist_ok=True)
ROOT = D.parent.parent
SAMPLES = ROOT / "data" / "samples"
BASE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else "http://localhost:8110"
ONLY = [a for a in sys.argv[1:] if not a.startswith("http")]
DUR = json.loads((D / "audio" / "durations.json").read_text())

INIT_JS = r"""
(() => {
  const css = `
  html, * { scroll-behavior: smooth; }
  #fs-ring { position: fixed; z-index: 2147483647; left: 0; top: 0; width: 34px; height: 34px; margin: -17px 0 0 -17px;
    border: 3px solid #E0A21A; border-radius: 50%; background: rgba(224,162,26,.18); pointer-events: none;
    transition: transform .08s linear, background .15s, border-color .15s; box-shadow: 0 0 0 2px rgba(255,255,255,.8); }
  #fs-ring.down { transform: scale(.6); background: rgba(224,162,26,.55); }
  .fs-ripple { position: fixed; z-index: 2147483646; width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%;
    border: 3px solid #E0A21A; pointer-events: none; animation: fsr .6s ease-out forwards; }
  @keyframes fsr { to { transform: scale(5); opacity: 0; } }`;
  const boot = () => {
    if (document.getElementById('fs-ring')) return;
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const r = document.createElement('div'); r.id = 'fs-ring'; r.style.display = 'none'; document.body.appendChild(r);
    addEventListener('mousemove', e => { r.style.display = 'block'; r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => { r.classList.add('down'); const d = document.createElement('div'); d.className = 'fs-ripple';
      d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; document.body.appendChild(d); setTimeout(() => d.remove(), 700); }, true);
    addEventListener('mouseup', () => r.classList.remove('down'), true);
  };
  if (document.body) boot(); else addEventListener('DOMContentLoaded', boot);
})();
"""


class Scene:
    def __init__(self, pw, browser, sid, viewport, scale=1, mobile=False):
        self.sid = sid
        self.t_ctx = time.time()
        self.ctx = browser.new_context(
            viewport=viewport, device_scale_factor=scale, is_mobile=mobile, has_touch=mobile,
            record_video_dir=str(RAW / "_tmp"), record_video_size=viewport, color_scheme="light",
        )
        self.ctx.add_init_script(INIT_JS)
        self.page: Page = self.ctx.new_page()
        self.t0 = None
        self.mx, self.my = viewport["width"] // 2, viewport["height"] // 2

    def goto(self, path):
        self.page.goto(BASE + path, wait_until="networkidle")
        self.page.wait_for_timeout(700)

    def start(self):
        self.t0 = time.time()
        self.lead = self.t0 - self.t_ctx

    def at(self, t):
        """Wait until t seconds after scene start (keeps actions aligned with narration)."""
        left = t - (time.time() - self.t0)
        if left > 0:
            self.page.wait_for_timeout(int(left * 1000))

    def pause(self, s):
        self.page.wait_for_timeout(int(s * 1000))

    def move(self, x, y, steps=28):
        self.page.mouse.move(x, y, steps=steps)
        self.mx, self.my = x, y

    def hover(self, loc, steps=28):
        loc.evaluate("""e => { const r = e.getBoundingClientRect();
            if (r.top < 90 || r.bottom > innerHeight - 90) e.scrollIntoView({behavior:'instant', block:'center'}); }""")
        self.pause(0.4)
        b = loc.bounding_box()
        self.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps)

    def click(self, loc, steps=28, after=0.5):
        self.hover(loc, steps)
        self.pause(0.25)
        self.page.mouse.down(); self.pause(0.08); self.page.mouse.up()
        self.pause(after)

    def scroll_to(self, loc, block="start", wait=1.2):
        loc.evaluate("e => e.scrollIntoView({behavior:'smooth', block:'%s'})" % block)
        self.pause(wait)

    def finish(self):
        elapsed = time.time() - self.t0
        video = self.page.video
        self.page.close(); self.ctx.close()
        final = RAW / f"{self.sid}.webm"
        if final.exists():
            final.unlink()
        Path(video.path()).rename(final)
        return {"trim": round(self.lead, 2), "seconds": round(elapsed, 2)}


def reset_state():
    import urllib.request
    urllib.request.urlopen(urllib.request.Request(BASE + "/api/demo/reset", method="POST", data=b""))


DESK = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}
state = {"msg": None}


def s1_chemist(pw, br):
    s = Scene(pw, br, "s1_chemist", DESK)
    s.goto("/chemist"); s.start()
    p = s.page
    s.at(1.5)
    s.hover(p.get_by_role("button", name="Voice note 2"))
    s.at(3.5)
    s.click(p.get_by_role("button", name="Voice note 2"), after=2.0)
    p.get_by_text("Sent. It is now in the distributor").wait_for(timeout=15000)
    s.at(8.0)
    s.click(p.get_by_role("button", name="Open the distributor inbox"), after=1.5)
    p.wait_for_url("**/distributor/inbox?msg=*", timeout=10000)
    state["msg"] = p.url.split("msg=")[1]
    s.at(DUR["s1_chemist"] + 0.5)
    return s.finish()


def s2_inbox(pw, br):
    s = Scene(pw, br, "s2_inbox", DESK)
    s.goto(f"/distributor/inbox?msg={state['msg']}"); s.start()
    p = s.page
    p.get_by_text("Check 1 line before you approve.").wait_for(timeout=20000)
    s.at(2.0)
    s.hover(p.get_by_text("HINDI TRANSCRIPT"), 20)
    s.at(5.5)
    pick = p.get_by_role("button", name="Pick product")
    s.scroll_to(pick, "center", 1.4)
    s.at(8.0)
    s.click(pick, after=1.0)
    opt = p.get_by_role("option").first
    s.hover(opt)
    s.at(12.0)
    s.click(opt, after=1.2)
    s.at(14.0)
    ap = p.get_by_role("button", name="Approve and send to billing")
    s.click(ap, after=1.5)
    s.at(17.0)
    s.page.get_by_role("link", name="Audit log").first.click()
    s.pause(1.5)
    s.at(DUR["s2_inbox"] + 0.5)
    return s.finish()


def s3_radar(pw, br):
    s = Scene(pw, br, "s3_radar", DESK)
    s.goto("/distributor/radar"); s.start()
    p = s.page
    s.at(1.5)
    d = p.get_by_role("button", name="Diarrhoea and vomiting")
    s.click(d, after=1.2)
    s.at(4.5)
    for _ in range(3):
        p.mouse.wheel(0, 120); s.pause(0.9)
    s.at(8.0)
    for _ in range(4):
        p.mouse.wheel(0, 120); s.pause(0.9)
    s.at(DUR["s3_radar"] + 0.5)
    return s.finish()


def s4_officer(pw, br):
    s = Scene(pw, br, "s4_officer", DESK)
    s.goto("/officer"); s.start()
    p = s.page
    s.at(1.5)
    s.hover(p.get_by_role("button", name="Kurla East / Nehru Nagar 400024, alert"))
    s.at(3.5)
    s.click(p.locator('a[href*="diarrhoea-400024"]').first, after=2.0)
    p.get_by_text("Explained by Gemini").wait_for(timeout=20000)
    s.at(6.5)
    s.scroll_to(p.get_by_role("heading", name="Why we think this"), "start", 1.5)
    s.at(10.0)
    s.scroll_to(p.get_by_role("heading", name="Drafted actions"), "start", 1.5)
    s.at(13.0)
    s.scroll_to(p.get_by_role("heading", name="ASHA visit list"), "start", 1.5)
    s.at(14.5)
    s.click(p.get_by_role("button", name="Approve action").last, after=1.5)
    s.at(DUR["s4_officer"] + 0.8)
    return s.finish()


def asha_report(s, worker, locality):
    p = s.page
    if p.get_by_role("button", name=worker).count() == 0:
        p.locator("button", has_text="Not you?").click(); s.pause(0.8)
    s.click(p.get_by_role("button", name=worker), after=1.2)
    card = p.locator("li", has=p.get_by_role("heading", name=locality)).get_by_role("button")
    if card.count() == 0:
        p.screenshot(path=str(RAW / "debug.png"))
    s.click(card, after=1.0)
    p.set_input_files("input[type=file]", str(SAMPLES / "asha_01.mp3"))
    s.pause(0.8)
    s.click(p.get_by_role("button", name="Send"), after=0.5)
    p.get_by_text("क्या यह सही है?").wait_for(timeout=30000)
    s.pause(2.0)
    p.mouse.wheel(0, 200); s.pause(1.2)
    s.click(p.locator("button", has_text="Yes, correct"), after=1.0)
    p.get_by_text("आपकी रिपोर्ट मिल गई").wait_for(timeout=15000)
    s.pause(2.5)
    p.mouse.wheel(0, 200); s.pause(1.0)


def s5_asha(pw, br):
    s = Scene(pw, br, "s5_asha", PHONE, scale=2, mobile=True)
    s.goto("/asha"); s.start()
    s.at(1.0)
    asha_report(s, "Rekha", "Nehru Nagar")
    s.at(9.0)
    s.click(s.page.locator("button", has_text="Next visit"), after=1.0)
    asha_report(s, "Lata", "Kapadia Nagar")
    s.at(DUR["s5_asha"] + 0.5)
    return s.finish()


def s6_backtest(pw, br):
    s = Scene(pw, br, "s6_backtest", DESK)
    s.goto("/officer/alert/diarrhoea-400024"); s.start()
    p = s.page
    s.at(1.5)
    s.scroll_to(p.get_by_role("heading", name="Back-test (simulated scenario)"), "start", 1.5)
    s.at(5.0)
    for _ in range(4):
        p.mouse.wheel(0, 150); s.pause(0.9)
    s.at(10.5)
    s.scroll_to(p.get_by_role("heading", name="Weather and air, last 30 days"), "start", 1.5)
    s.at(DUR["s6_backtest"] + 0.5)
    return s.finish()


SCENE_FUNCS = [("s1_chemist", s1_chemist), ("s2_inbox", s2_inbox), ("s3_radar", s3_radar),
               ("s4_officer", s4_officer), ("s5_asha", s5_asha), ("s6_backtest", s6_backtest)]

if __name__ == "__main__":
    tfile = RAW / "timing.json"
    timing = json.loads(tfile.read_text()) if tfile.exists() else {}
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        if not ONLY:
            reset_state()
        for sid, fn in SCENE_FUNCS:
            if ONLY and sid not in ONLY:
                continue
            if sid == "s2_inbox" and not state["msg"]:
                m = RAW / "msg.txt"
                state["msg"] = m.read_text().strip() if m.exists() else None
            print("recording", sid, flush=True)
            timing[sid] = fn(pw, br)
            if state["msg"]:
                (RAW / "msg.txt").write_text(state["msg"])
            print(sid, timing[sid], flush=True)
            tfile.write_text(json.dumps(timing, indent=1))
        br.close()
