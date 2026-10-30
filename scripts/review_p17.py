#!/usr/bin/env python3
"""17차 검수: python scripts/review_p17.py [--output ref/review-p17].

필수: Python 3.10+, Node.js, Playwright Python, Chromium.
브라우저 설치 경로는 --chromium으로 지정한다. 외부 요청·의견 전송은 하지 않는다.
수치 대조는 Fraction의 원점 적률 및 표지 구슬 순서쌍 열거로 독립 계산한다.
"""

import argparse
from fractions import Fraction
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Thread
from urllib.parse import quote

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def text_number(page, selector):
    value = page.locator(selector).inner_text().replace("−", "-").replace(",", "")
    return float(re.search(r"-?\d+(?:\.\d+)?", value)[0])


def set_range(page, selector, value):
    page.locator(selector).evaluate(
        "(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));}", value
    )
    assert abs(float(page.locator(selector).input_value()) - value) < 1e-8, (selector, value)


def jump(page, sid):
    """Use the actual navigation buttons; do not call the module's private show()."""
    distance = page.evaluate("""id=>{
      const slides=[...document.querySelectorAll('.slide')];
      return slides.indexOf(document.getElementById(id))-slides.indexOf(document.querySelector('.slide.on'));
    }""", sid)
    for _ in range(abs(distance)):
        page.locator("#next" if distance > 0 else "#prev").click()
    assert page.locator(".slide.on").get_attribute("id") == sid


def layout(page, context, failures):
    issues = page.evaluate("""()=>{
      const slide=document.querySelector('.slide.on'), out=[];
      for(const e of slide.querySelectorAll('.body,.side,.math,.exp,.fbp,.think,.pmsg,.plabel,.gl,.gi,.gmap,.ctrl')){
        if(e.clientHeight>0 && (e.scrollHeight>e.clientHeight+3 || e.scrollWidth>e.clientWidth+3))
          out.push({type:'overflow',tag:e.id||e.className,h:[e.clientHeight,e.scrollHeight],w:[e.clientWidth,e.scrollWidth]});
      }
      for(const svg of slide.querySelectorAll('svg[viewBox]')){
        const v=svg.viewBox.baseVal;
        for(const t of svg.querySelectorAll('text')){
          const b=t.getBBox();
          if(b.width && (b.x<v.x-2 || b.y<v.y-2 || b.x+b.width>v.x+v.width+2 || b.y+b.height>v.y+v.height+2))
            out.push({type:'svg-clip',svg:svg.id,text:t.textContent});
        }
      }
      return out;
    }""")
    failures.extend(dict(context=context, **issue) for issue in issues)


def expanded_help(page, context, failures):
    details = page.locator(".slide.on details")
    for index in range(details.count()):
        details.nth(index).locator("summary").click()
        layout(page, context + " expanded", failures)
        details.nth(index).locator("summary").click()


def audit_module(page, number, failures):
    path = next((ROOT / "module_v1").glob(f"M{number:02}_*.html"))
    source = path.read_text()
    quizzes = page.evaluate("(" + re.search(r"var QUIZ=(\[.*?\n\]);", source, re.S)[1] + ")")
    assert len(quizzes) == 6 and [q["goal"] for q in quizzes] == [1, 1, 2, 2, 3, 3]
    if number == 6:
        assert quizzes[2]["opts"][quizzes[2]["ans"]] == "180원, 25,600원²"
        assert Fraction(quizzes[5]["opts"][quizzes[5]["ans"]]) == Fraction(1, 4)
    if number == 7:
        assert quizzes[2]["opts"][quizzes[2]["ans"]] == "z=2, T=70"
    assert page.evaluate("""()=>{
      const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);
      return ids.length===new Set(ids).size;
    }""")
    page.locator(".station").nth(1).click()
    goals = page.locator(".gmap .gn")
    assert goals.count() == 3
    links = page.locator(".gmap [data-jump]").evaluate_all(
        "es=>es.map(e=>({id:e.dataset.jump,label:e.textContent.trim()}))"
    )
    assert len(links) == (7 if number == 6 else 6)
    for index, link in enumerate(links):
        page.locator(".station").nth(1).click()
        page.locator('.gmap [data-jump]').nth(index).click()
        assert page.locator(".slide.on").get_attribute("id") == link["id"]
    page.locator(".station").nth(0).click()
    slides = page.locator(".slide").count()
    for index in range(slides):
        current = page.locator(".slide.on")
        sid = current.get_attribute("id") or f"slide-{index}"
        context = f"M{number:02} {sid}"
        layout(page, context, failures)
        if re.fullmatch(r"q[1-6]", sid):
            quiz = quizzes[int(sid[1:]) - 1]
            current.locator(".opts button").nth(quiz["ans"]).click()
            assert current.locator(".fbp.ok").count() == 1
            layout(page, context + " answered", failures)
            current.locator(".back").click()
            assert page.locator(".slide.on").get_attribute("id") == quiz["back"]
            jump(page, sid)
        if sid in ("p1", "p2", "p3"):
            expanded_help(page, context, failures)
        if index < slides - 1:
            page.locator("#next").click()
    jump(page, "p2")
    cards = page.locator("#p2-pool .dcard")
    count = cards.count()
    for _ in range(count):
        card = page.locator("#p2-pool .dcard").first
        answer = card.get_attribute("data-ans")
        if number == 5:
            value = int(card.inner_text().replace("점", "").replace("−", "-"))
            expected = "이상값 · 기록 실수 의심" if not 0 <= value <= 100 else "이상값 · 실제일 수 있음" if abs(value - 60) >= 20 else "2SD 미만"
            assert answer == expected
        card.focus()
        card.press("Enter")
        page.get_by_role("button", name=answer + " 칸에 놓기", exact=True).press("Enter")
    assert page.locator("#p2-count").inner_text() == f"{count} / {count}"
    page.locator("#p2-reset").click()
    assert page.locator("#p2-pool .dcard").count() == count
    return dict(module=number, slides=slides, quizzes=6, cards=count, goal_links=len(links))


def mean_checks(page, failures):
    jump(page, "p1")
    page.locator("#p1-items button").nth(9).click()
    results = []
    for value in (0, 1.9, 4.2, 8):
        set_range(page, "#p1-range", value)
        expected_sum = Fraction(203, 10) - Fraction(42, 10) + Fraction(str(value))
        assert abs(text_number(page, "#p1-sum") - float(expected_sum)) < 1e-9
        assert abs(text_number(page, "#p1-mean") - float(expected_sum / 12)) <= .0051
        layout(page, f"M01 tenth value {value}", failures)
        results.append([value, float(expected_sum / 12)])
    page.locator("#p1-reset").click()
    return results


def bag_checks(page, failures):
    jump(page, "p1")
    results = []
    for red in range(10):
        for white in range(10):
            set_range(page, "#m6-r", red)
            set_range(page, "#m6-w", white)
            if not red + white:
                assert [page.locator(s).inner_text() for s in ("#m6-pr", "#m6-pw", "#m6-e", "#m6-v")] == ["-"] * 4
            else:
                pr, pw = Fraction(red, red + white), Fraction(white, red + white)
                mean = 100 * pr + 500 * pw
                variance = 100**2 * pr + 500**2 * pw - mean**2
                assert abs(text_number(page, "#m6-e") - float(mean)) <= .051
                assert abs(text_number(page, "#m6-v") - float(variance)) <= .051
                assert Fraction(page.locator("#m6-pr").inner_text()) == pr
                assert Fraction(page.locator("#m6-pw").inner_text()) == pw
                results.append([red, white, float(mean), float(variance)])
            layout(page, f"M06 bag {red}/{white}", failures)
    set_range(page, "#m6-r", 4)
    set_range(page, "#m6-w", 1)
    assert text_number(page, "#m6-v") == 25600
    expanded_help(page, "M06 bag default", failures)
    # Enumerate distinct labelled marbles, rather than reuse the module formula.
    pairs = [(a, b) for a in range(5) for b in range(5) if a != b]
    condition = [(a, b) for a, b in pairs if a < 4]
    conditional = Fraction(sum(b == 4 for a, b in condition), len(condition))
    assert conditional == Fraction(1, 4)
    return dict(settings=100, nonempty_results=results, conditional_probability=str(conditional))


def score_checks(page, failures):
    jump(page, "p3")
    values = [(180, 167.6, 7), (170, 154.1, 6.9), (160.6, 167.6, 7),
              (147.2, 154.1, 6.9), (188.6, 167.6, 7), (161, 154.1, 6.9)]
    results = []
    for mode in ("z", "T"):
        page.locator("#m7-scale").select_option(mode)
        for index, (height, mean, sd) in enumerate(values):
            z = (height - mean) / sd
            expected = z if mode == "z" else 50 + 10 * z
            guesses = [-3, 3, round(z, 1)] if mode == "z" else [20, 80, round(expected)]
            assert page.locator("#m7-act").inner_text() == "?"
            for guess in guesses:
                set_range(page, "#m7-g", guess)
                assert page.locator("#m7-act").inner_text() == "?"
                assert "ok" not in page.locator("#m7-msg3").get_attribute("class")
                page.locator("#m7-check").click()
                assert abs(text_number(page, "#m7-act") - expected) <= .0051
                dz = abs((guess if mode == "z" else (guess - 50) / 10) - z)
                assert ("ok" in page.locator("#m7-msg3").get_attribute("class")) == (dz <= .2)
                # Check the plotted prediction marker in original cm coordinates.
                actual_x = float(re.search(r"M([\d.]+)", page.locator("#m7-p3-svg path[fill='#1B2A4A']").get_attribute("d"))[1])
                expect_x = 20 + ((guess if mode == "z" else (guess - 50) / 10) + 3.6) / 7.2 * 430
                assert abs(actual_x - expect_x) < 1e-6
                layout(page, f"M07 {mode} person {index + 1} guess {guess}", failures)
                results.append([mode, index + 1, guess, expected])
            expanded_help(page, f"M07 {mode} person {index + 1}", failures)
            page.locator("#m7-nextq").click()
            assert page.locator("#m7-g").input_value() == ("0" if mode == "z" else "50")
    page.locator("#m7-check").click()
    page.locator("#m7-scale").select_option("z")
    assert page.locator("#m7-act").inner_text() == "?" and page.locator("#m7-g").input_value() == "0"
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "ref/review-p17")
    parser.add_argument("--chromium", default=shutil.which("chromium"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "result.json").unlink(missing_ok=True)
    assert args.chromium, "Chromium path required (--chromium)"
    for path in sorted((ROOT / "module_v1").glob("M0[1-7]_*.html")):
        script = re.search(r"<script>(.*?)</script>", path.read_text(), re.S)[1]
        with tempfile.TemporaryDirectory() as temp:
            js = Path(temp) / "module.js"
            js.write_text(script)
            subprocess.run(["node", "--check", str(js)], check=True, capture_output=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    failures, errors, modules = [], [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
            page.on("pageerror", lambda error: errors.append(str(error)))
            for number in range(1, 8):
                path = next((ROOT / "module_v1").glob(f"M{number:02}_*.html"))
                page.goto(f"http://127.0.0.1:{server.server_port}/" + quote(str(path.relative_to(ROOT))))
                modules.append(audit_module(page, number, failures))
                if number == 1:
                    means = mean_checks(page, failures)
                if number == 6:
                    bag = bag_checks(page, failures)
                if number == 7:
                    scores = score_checks(page, failures)
                if number in (1, 3, 4, 5, 6, 7):
                    jump(page, "p1" if number in (1, 6) else "p2" if number in (4, 5) else "p3")
                    if number == 7:
                        page.locator("#m7-scale").select_option("T")
                        set_range(page, "#m7-g", 68)
                        page.locator("#m7-check").click()
                    page.locator(".slide.on details summary").first.click()
                    page.screenshot(path=str(args.output / f"M{number:02}-practice.png"))
                if number == 6:
                    page.locator(".station").nth(1).click()
                    page.screenshot(path=str(args.output / "M06-goals.png"))
            browser.close()
        result = dict(modules=modules, means=means, bag=bag, scores=scores, failures=failures, pageerrors=errors)
        (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(dict(modules=modules, bag_settings=100, score_settings=len(scores), failures=len(failures), pageerrors=errors), ensure_ascii=False, indent=2))
        assert not failures, failures[:8]
        assert not errors, errors
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
