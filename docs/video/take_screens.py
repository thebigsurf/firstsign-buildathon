"""Fresh deck screenshots into docs/screens/ (light theme, clean state). Usage: python take_screens.py [base_url]"""
import sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "screens"
SAMPLES = ROOT / "data" / "samples"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8110"
DESK = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}


def reset():
    urllib.request.urlopen(urllib.request.Request(BASE + "/api/demo/reset", method="POST", data=b""))


def scroll(page, loc, block="start", offset=0):
    loc.evaluate("e => e.scrollIntoView({behavior:'instant', block:'%s'})" % block)
    if offset:
        page.evaluate("o => window.scrollBy(0, o)", offset)
    page.wait_for_timeout(500)


def snap(page, name):
    page.screenshot(path=str(OUT / name))
    print("saved", name, flush=True)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    reset()
    ctx = br.new_context(viewport=DESK, color_scheme="light")
    p = ctx.new_page()

    def go(path, wait=1200):
        p.goto(BASE + path, wait_until="networkidle"); p.wait_for_timeout(wait)

    go("/"); snap(p, "01_landing.png")

    go("/chemist")
    p.get_by_role("button", name="Voice note 2").click()
    p.get_by_text("Sent. It is now in the distributor").wait_for(timeout=15000)
    p.wait_for_timeout(1200)
    scroll(p, p.get_by_role("heading", level=1), "start")
    snap(p, "02_chemist_send.png")

    go("/distributor/inbox?msg=msg_05", 500)
    p.get_by_text("Check 1 line before you approve.").wait_for(timeout=20000)
    p.wait_for_timeout(800)
    scroll(p, p.get_by_text("UNSURE").first if p.get_by_text("UNSURE").count() else p.get_by_text("Check 1 line before you approve."), "start", -60)
    snap(p, "03_inbox_parsed_yellow_line.png")

    go("/distributor/radar", 1500)
    p.get_by_role("button", name="Diarrhoea and vomiting").click(); p.wait_for_timeout(1000)
    snap(p, "04_radar.png")

    go("/officer", 2500); snap(p, "05_officer_map.png")

    go("/officer/alert/diarrhoea-400024", 3500)
    snap(p, "06_alert_detail_top.png")
    scroll(p, p.get_by_role("heading", name="Drafted actions"), "start", -20)
    snap(p, "07_alert_drafted_actions.png")
    scroll(p, p.get_by_role("heading", name="Back-test (simulated scenario)"), "start", -20)
    snap(p, "08_backtest_panel.png")
    scroll(p, p.get_by_role("heading", name="Weather and air, last 30 days"), "start", -20)
    snap(p, "08b_weather_air_real.png")
    # approve the visit list so the ASHA phone sees it
    scroll(p, p.get_by_role("heading", name="ASHA visit list"), "start", -20)
    p.get_by_role("button", name="Approve action").last.click(); p.wait_for_timeout(1500)
    ctx.close()

    pctx = br.new_context(viewport=PHONE, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme="light")
    a = pctx.new_page()
    a.goto(BASE + "/asha", wait_until="networkidle"); a.wait_for_timeout(800)
    a.get_by_role("button", name="Rekha").click(); a.wait_for_timeout(1500)
    snap(a, "09_asha_visit_list_phone.png")
    a.locator("li", has=a.get_by_role("heading", name="Nehru Nagar")).get_by_role("button").click(); a.wait_for_timeout(800)
    a.set_input_files("input[type=file]", str(SAMPLES / "asha_01.mp3")); a.wait_for_timeout(600)
    a.get_by_role("button", name="Send").click()
    a.get_by_text("क्या यह सही है?").wait_for(timeout=30000); a.wait_for_timeout(1000)
    snap(a, "10_asha_structured_report_phone.png")
    pctx.close()

    cctx = br.new_context(viewport=PHONE, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme="light")
    c = cctx.new_page()
    c.goto(BASE + "/chemist", wait_until="networkidle"); c.wait_for_timeout(1000)
    c.get_by_role("button", name="Voice note 2").click()
    c.get_by_text("Sent. It is now in the distributor").wait_for(timeout=15000); c.wait_for_timeout(1500)
    c.evaluate("window.scrollTo(0, 0)"); c.wait_for_timeout(300)
    snap(c, "11_chemist_send_phone.png")
    br.close()
    reset()
