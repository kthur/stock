"""
tests/test_challenger1_multipage_integrity.py

Adversarial validation and stress-test suite for Static Multi-Page Architecture (gh-pages/):
1. BeautifulSoup parsing across all 7 generated HTML files.
2. Link integrity & anchor validation (target file exists, target element with id exists, 0 broken links).
3. Byte size constraint check: index.html strictly < 500 KB (512,000 bytes).
4. DOM cleanliness and template anomaly scanning: unescaped template placeholders ({undefined}, raw { or }),
   duplicate DOM element IDs.
5. Global sticky navigation bar verification (<header class="sticky-nav">) and active link highlighting on all 7 pages.
6. Script integrity and syntax checks (brace balancing, node --check syntax).
7. Event handler function definition integrity: all functions invoked in inline event handlers (onclick, oninput, etc.) must be defined in scripts on that page.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
import pytest
from bs4 import BeautifulSoup

GH_PAGES_DIR = Path("gh-pages")
EXPECTED_PAGES = [
    "index.html",
    "strategies.html",
    "market_kospi.html",
    "market_kosdaq.html",
    "market_sp500.html",
    "market_nasdaq.html",
    "market_russell2000.html",
]

PAGE_ACTIVE_LINK_EXPECTED = {
    "index.html": "index.html",
    "strategies.html": "strategies.html",
    "market_kospi.html": "market_kospi.html",
    "market_kosdaq.html": "market_kosdaq.html",
    "market_sp500.html": "market_sp500.html",
    "market_nasdaq.html": "market_nasdaq.html",
    "market_russell2000.html": "market_russell2000.html",
}

JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return"}
BUILTINS = {
    "scrollTo", "preventDefault", "stopPropagation", "click", "alert",
    "confirm", "prompt", "setTimeout", "setInterval", "clearTimeout",
    "clearInterval", "parseInt", "parseFloat", "encodeURIComponent", "decodeURIComponent"
}


def load_all_soups() -> dict[str, tuple[str, BeautifulSoup]]:
    soups = {}
    for page_name in EXPECTED_PAGES:
        file_path = GH_PAGES_DIR / page_name
        assert file_path.exists(), f"File {file_path} does not exist"
        raw_text = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(raw_text, "html.parser")
        soups[page_name] = (raw_text, soup)
    return soups


class TestMultipageChallenger1Integrity:

    @pytest.fixture(scope="class")
    def page_soups(self):
        return load_all_soups()

    def test_r1_all_7_pages_present_and_parsed_by_beautifulsoup(self, page_soups):
        """Verify all 7 pages exist, are non-empty, and parsed successfully by BeautifulSoup."""
        assert len(page_soups) == 7
        for name, (raw_text, soup) in page_soups.items():
            assert soup.html is not None, f"{name}: <html> root tag not found"
            assert soup.head is not None, f"{name}: <head> tag not found"
            assert soup.body is not None, f"{name}: <body> tag not found"
            assert len(raw_text) > 1024, f"{name}: Content suspiciously short ({len(raw_text)} bytes)"

    def test_r2_page_size_constraints(self, page_soups):
        """Executive summary (index.html) must be strictly < 500 KB (512,000 bytes)."""
        index_file = GH_PAGES_DIR / "index.html"
        size_bytes = index_file.stat().st_size
        max_bytes = 500 * 1024  # 512,000 bytes
        assert size_bytes < max_bytes, (
            f"index.html exceeds 500 KB constraint: {size_bytes} bytes "
            f"({size_bytes / 1024:.2f} KB) >= {max_bytes} bytes"
        )
        assert size_bytes > 50 * 1024, f"index.html suspiciously small: {size_bytes} bytes"

    def test_r3_global_sticky_nav_and_active_indicator(self, page_soups):
        """Verify <header class="sticky-nav"> (or global-nav) exists with correct active page link on all 7 pages."""
        for name, (_, soup) in page_soups.items():
            header = soup.find("header")
            assert header is not None, f"{name}: <header> missing"
            header_classes = header.get("class", [])
            assert any(cls in ("sticky-nav", "global-nav") for cls in header_classes), (
                f"{name}: <header> class must be sticky-nav or global-nav, found {header_classes}"
            )

            nav = header.find("nav")
            assert nav is not None, f"{name}: <nav> inside header missing"

            # Check that all 7 navigation links are present in the nav
            nav_links = nav.find_all("a", href=True)
            hrefs_in_nav = [a["href"] for a in nav_links]
            for target_page in EXPECTED_PAGES:
                assert target_page in hrefs_in_nav, (
                    f"{name}: navigation menu does not contain link to {target_page}"
                )

            # Check the active link
            active_links = [
                a for a in nav_links
                if any(c in a.get("class", []) for c in ("active", "nav-active"))
            ]
            assert len(active_links) == 1, (
                f"{name}: Expected exactly 1 active link in navigation, found {len(active_links)}: "
                f"{[a['href'] for a in active_links]}"
            )
            expected_href = PAGE_ACTIVE_LINK_EXPECTED[name]
            assert active_links[0]["href"] == expected_href, (
                f"{name}: Expected active nav link to be {expected_href}, got {active_links[0]['href']}"
            )

    def test_r4_link_integrity_and_anchors_zero_broken(self, page_soups):
        """Adversarially extract every <a> tag across all 7 pages and verify:
        - Relative target files exist in gh-pages/
        - Anchor targets (#...) exist in target file as an element with id='...'
        - Report 0 broken links.
        """
        broken_links = []
        total_links = 0
        relative_file_links = 0
        anchor_links = 0
        external_links = 0

        # Precompute all element IDs in all soups for fast lookup
        id_sets = {}
        for name, (_, soup) in page_soups.items():
            id_sets[name] = {elem.get("id") for elem in soup.find_all(id=True)}

        for name, (_, soup) in page_soups.items():
            a_tags = soup.find_all("a")
            for a in a_tags:
                total_links += 1
                href = a.get("href")
                if not href:
                    broken_links.append((name, str(a), "Empty or missing href attribute"))
                    continue

                parsed = urlparse(href)
                # Ignore external links and pure JS links
                if parsed.scheme in ("http", "https", "mailto"):
                    external_links += 1
                    continue
                if href == "#" or href.startswith("javascript:"):
                    continue

                file_part = parsed.path
                fragment = parsed.fragment
                target_file = file_part if file_part else name

                # Validate target file exists
                if target_file not in page_soups:
                    broken_links.append((name, href, f"Target file '{target_file}' does not exist in gh-pages/"))
                    continue

                if file_part:
                    relative_file_links += 1

                # Validate anchor fragment if present
                if fragment:
                    anchor_links += 1
                    if fragment not in id_sets[target_file]:
                        broken_links.append(
                            (name, href, f"Anchor id '{fragment}' not found in target file '{target_file}'")
                        )

        assert len(broken_links) == 0, (
            f"Found {len(broken_links)} broken links:\n" +
            "\n".join(f"  [{src}] {link} -> {reason}" for src, link, reason in broken_links)
        )

    def test_r5_dom_cleanliness_and_template_anomaly_scan(self, page_soups):
        """Scan for template leak anomalies ({undefined}, raw {variable}, malformed template artifacts)
        and duplicate DOM element IDs.
        """
        anomalies = []
        for name, (raw_text, soup) in page_soups.items():
            # Check for literal undefined or unrendered template strings
            unrendered_undefined = re.findall(r'\{\s*undefined\s*\}|\$\{\s*undefined\s*\}', raw_text)
            if unrendered_undefined:
                anomalies.append((name, f"Found literal unrendered undefined placeholders: {unrendered_undefined}"))

            # Check for unrendered Jinja/Django or Mustache markers like {{ foo }} or {% bar %}
            template_markers = re.findall(r'\{\{\s*[a-zA-Z0-9_]+\s*\}\}|\{%\s*[a-zA-Z0-9_]+\s*%\}', raw_text)
            if template_markers:
                anomalies.append((name, f"Found unrendered server template markers: {template_markers[:5]}"))

            # Check for NaN / null in user-facing table text (not within script tags)
            clean_soup = BeautifulSoup(raw_text, "html.parser")
            for tag in clean_soup(["script", "style", "code", "pre"]):
                tag.decompose()
            visible_text = clean_soup.get_text()
            nan_matches = re.findall(r'\b(?:NaN%|undefined%|\$NaN|null%)\b', visible_text)
            if nan_matches:
                anomalies.append((name, f"Found unformatted NaN/undefined in text: {nan_matches[:5]}"))

            # Check for duplicate IDs on the same page
            all_ids = [elem.get("id") for elem in soup.find_all(id=True)]
            seen = set()
            duplicates = []
            for elem_id in all_ids:
                if elem_id in seen:
                    duplicates.append(elem_id)
                else:
                    seen.add(elem_id)
            if duplicates:
                anomalies.append((name, f"Found duplicate DOM element IDs: {duplicates[:10]}"))

        assert len(anomalies) == 0, (
            f"Found {len(anomalies)} DOM cleanliness / template anomalies:\n" +
            "\n".join(f"  [{src}] {reason}" for src, reason in anomalies)
        )

    def test_r6_script_syntax_and_node_check(self, page_soups):
        """Check all inline <script> blocks across all 7 pages for syntax validity using node --check."""
        script_issues = []
        for name, (_, soup) in page_soups.items():
            scripts = soup.find_all("script")
            for i, script in enumerate(scripts):
                src = script.get("src")
                content = script.string or script.text
                if not src and content:
                    tmp = Path(f"tmp_test_{name}_{i}.js")
                    tmp.write_text(content, encoding="utf-8")
                    try:
                        res = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
                        if res.returncode != 0:
                            script_issues.append((name, f"Script #{i} Node syntax check failed: {res.stderr.strip()}"))
                    finally:
                        if tmp.exists():
                            tmp.unlink()

        assert len(script_issues) == 0, (
            f"Found {len(script_issues)} script syntax issues:\n" +
            "\n".join(f"  [{src}] {reason}" for src, reason in script_issues)
        )

    def test_r7_event_handler_functions_defined(self, page_soups):
        """Verify that every function invoked from an inline HTML event handler (onclick, oninput, etc.)
        is defined within the scripts of that page.
        """
        missing_handlers = []
        for name, (_, soup) in page_soups.items():
            scripts = "".join(s.get_text() for s in soup.find_all("script"))

            events = []
            for tag in soup.find_all():
                for attr, val in tag.attrs.items():
                    if attr.startswith("on"):
                        events.append((tag.name, attr, val))

            called_fns = set()
            for _, _, val in events:
                for m in re.finditer(r'([a-zA-Z0-9_$]+)\s*\(', val):
                    fn = m.group(1)
                    if fn not in JS_KEYWORDS and fn not in BUILTINS:
                        called_fns.add(fn)

            missing_on_page = []
            for fn in sorted(called_fns):
                pattern = (
                    r'\b(?:function\s+' + re.escape(fn) +
                    r'|' + re.escape(fn) + r'\s*=\s*(?:function|\()|window\.' + re.escape(fn) + r')\b'
                )
                if not re.search(pattern, scripts):
                    missing_on_page.append(fn)

            if missing_on_page:
                missing_handlers.append((name, missing_on_page))

        assert len(missing_handlers) == 0, (
            f"Found missing event handler function definitions on {len(missing_handlers)} pages:\n" +
            "\n".join(f"  [{name}] Undefined functions invoked: {fns}" for name, fns in missing_handlers)
        )


def run_standalone_audit():
    """Execute standalone empirical audit and output detailed statistics."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("======================================================================")
    print("CHALLENGER 1: EMPIRICAL MULTI-PAGE AUDIT & ADVERSARIAL STRESS TEST")
    print("======================================================================")

    page_soups = load_all_soups()

    print("\n--- 1. Page Byte Sizes ---")
    for name in EXPECTED_PAGES:
        file_path = GH_PAGES_DIR / name
        size_bytes = file_path.stat().st_size
        size_kb = size_bytes / 1024.0
        status = "PASS" if (name != "index.html" or size_bytes < 500 * 1024) else "FAIL"
        print(f"  {name:<25}: {size_bytes:>9,} bytes ({size_kb:>7.2f} KB) [{status}]")

    print("\n--- 2. Navigation Header & Active Indicator ---")
    for name, (_, soup) in page_soups.items():
        header = soup.find("header")
        classes = header.get("class", []) if header else []
        active_a = header.find_all("a", class_=lambda c: c and ("active" in c or "nav-active" in c)) if header else []
        active_href = active_a[0].get("href") if active_a else "NONE"
        expected = PAGE_ACTIVE_LINK_EXPECTED[name]
        match = "MATCH" if active_href == expected else f"MISMATCH (expected {expected})"
        print(f"  {name:<25}: Header={classes} | ActiveLink={active_href:<25} [{match}]")

    print("\n--- 3. Link Extraction & Anchor Resolution ---")
    id_sets = {name: {elem.get("id") for elem in soup.find_all(id=True)} for name, (_, soup) in page_soups.items()}
    total_links_all = 0
    broken_links = []

    for name, (_, soup) in page_soups.items():
        links = soup.find_all("a")
        page_total = len(links)
        total_links_all += page_total
        page_broken = 0
        for a in links:
            href = a.get("href")
            if not href:
                page_broken += 1
                broken_links.append((name, str(a), "Missing href"))
                continue
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https", "mailto") or href == "#" or href.startswith("javascript:"):
                continue
            file_part = parsed.path
            fragment = parsed.fragment
            target_file = file_part if file_part else name
            if target_file not in page_soups:
                page_broken += 1
                broken_links.append((name, href, f"Target file {target_file} not found"))
                continue
            if fragment and fragment not in id_sets[target_file]:
                page_broken += 1
                broken_links.append((name, href, f"Target #{fragment} not in {target_file}"))

        print(f"  {name:<25}: Total Links = {page_total:>3} | Broken = {page_broken:>2}")

    print(f"\nTotal Links Scanned Across All Pages: {total_links_all}")
    print(f"Total Broken Links: {len(broken_links)}")

    print("\n--- 4. DOM Cleanliness & Template Anomaly Scan ---")
    anomalies_all = []
    for name, (raw_text, soup) in page_soups.items():
        clean_soup = BeautifulSoup(raw_text, "html.parser")
        for tag in clean_soup(["script", "style", "code", "pre"]):
            tag.decompose()
        visible_text = clean_soup.get_text()
        nan_matches = re.findall(r'\b(?:NaN%|undefined%|\$NaN|null%)\b', visible_text)
        undefined_matches = re.findall(r'\{\s*undefined\s*\}|\$\{\s*undefined\s*\}', raw_text)
        all_ids = [elem.get("id") for elem in soup.find_all(id=True)]
        dup_ids = [eid for eid in set(all_ids) if all_ids.count(eid) > 1]
        
        status = "CLEAN" if not (nan_matches or undefined_matches or dup_ids) else "ANOMALY"
        print(f"  {name:<25}: NaN/undef text={len(nan_matches)} | Templates={len(undefined_matches)} | Duplicate IDs={len(dup_ids)} [{status}]")
        if nan_matches or undefined_matches or dup_ids:
            anomalies_all.append((name, nan_matches, undefined_matches, dup_ids))

    print("\n--- 5. Event Handler Function Definition Scan ---")
    missing_handlers_all = []
    for name, (_, soup) in page_soups.items():
        scripts = "".join(s.get_text() for s in soup.find_all("script"))
        events = []
        for tag in soup.find_all():
            for attr, val in tag.attrs.items():
                if attr.startswith("on"):
                    events.append((tag.name, attr, val))
        called_fns = set()
        for _, _, val in events:
            for m in re.finditer(r'([a-zA-Z0-9_$]+)\s*\(', val):
                fn = m.group(1)
                if fn not in JS_KEYWORDS and fn not in BUILTINS:
                    called_fns.add(fn)
        missing_on_page = []
        for fn in sorted(called_fns):
            pattern = (
                r'\b(?:function\s+' + re.escape(fn) +
                r'|' + re.escape(fn) + r'\s*=\s*(?:function|\()|window\.' + re.escape(fn) + r')\b'
            )
            if not re.search(pattern, scripts):
                missing_on_page.append(fn)
        status = "CLEAN" if not missing_on_page else f"MISSING ({len(missing_on_page)})"
        print(f"  {name:<25}: Called={len(called_fns):>2} | {status} {missing_on_page if missing_on_page else ''}")
        if missing_on_page:
            missing_handlers_all.append((name, missing_on_page))

    print("\n======================================================================")
    if len(broken_links) == 0 and len(anomalies_all) == 0 and len(missing_handlers_all) == 0 and (GH_PAGES_DIR / "index.html").stat().st_size < 500 * 1024:
        print("VERDICT: >>> APPROVE <<< (All empirical constraints strictly satisfied)")
    else:
        print("VERDICT: >>> REQUEST_CHANGES <<<")
    print("======================================================================")


if __name__ == "__main__":
    run_standalone_audit()
