import functools
import http.server
import os
import socket
import threading
import time
import pytest
from playwright.sync_api import sync_playwright

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
DEFAULT_PORT = 4173


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress request log spam in test output


@pytest.fixture(scope="session")
def server_url():
    port = DEFAULT_PORT
    server = None
    thread = None

    if not is_port_open(port):
        handler = functools.partial(QuietHandler, directory=DOCS_DIR)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.3)

    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    if server:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def test_overview_page_desktop(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{server_url}/index.html")
    page.wait_for_load_state("networkidle")

    # Verify title & brand
    assert "JAV.guru" in page.title()
    assert page.locator("header").is_visible()

    # Verify KPIs
    kpi_count = page.locator("div.tabular-nums").count()
    assert kpi_count >= 5

    # Verify Command Palette keyboard shortcut
    page.keyboard.press("Meta+K")
    page.wait_for_timeout(300)
    cmd_dialog = page.locator("#cmd-dialog")
    assert cmd_dialog.is_visible()
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    assert not cmd_dialog.is_visible()

    # Test Theme Toggle
    theme_btn = page.locator("#theme-toggle-btn")
    theme_btn.click()
    page.wait_for_timeout(200)
    assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light"
    theme_btn.click()
    page.wait_for_timeout(200)
    assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "dark"

    context.close()


def test_navigation_and_directory_aliases(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    # Test both .html and directory / variants
    for path in ["/browse.html", "/browse/", "/sitemap.html", "/sitemap/"]:
        res = page.goto(f"{server_url}{path}")
        assert res.status == 200, f"Failed to load {path}, got status {res.status}"
        assert page.locator("header").is_visible()

    context.close()


def test_browse_catalogue_and_player(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{server_url}/browse.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify initial cards populated
    cards = page.locator("#cards-grid article")
    initial_count = cards.count()
    assert initial_count > 0, "No cards loaded in browse grid"

    # Test Search Filter with an existing item code
    target_code = cards.first.locator(".card-code").first.text_content().strip()
    assert len(target_code) > 0, "First card has empty code"

    search_input = page.locator("#search-input")
    search_input.fill(target_code)
    page.wait_for_timeout(500)

    filtered_cards = page.locator("#cards-grid article")
    filtered_count = filtered_cards.count()
    assert 0 < filtered_count <= initial_count, f"Expected 0 < {filtered_count} <= {initial_count}"

    # Verify search results actually match the query
    for i in range(min(filtered_count, 3)):
        card_text = filtered_cards.nth(i).text_content()
        assert target_code.lower() in card_text.lower(), f"Card missing query '{target_code}': {card_text}"

    # Test Search Filter with a non-existent query (assert empty state)
    search_input.fill("xyz_nonexistent_query_99999")
    page.wait_for_timeout(500)
    assert page.locator("#cards-grid article").count() == 0
    assert "No matching records found" in page.locator("#cards-grid").text_content()

    # Clear search and assert restored count
    search_input.fill("")
    page.wait_for_timeout(500)
    assert page.locator("#cards-grid article").count() == initial_count

    # Open Video Player modal
    first_card = page.locator("#cards-grid article").first
    first_card.locator(".aspect-\\[16\\/10\\]").click()
    page.wait_for_timeout(500)
    player_dialog = page.locator("#video-player-dialog")
    assert player_dialog.is_visible()
    page.locator("#close-player-btn").click()
    page.wait_for_timeout(300)
    assert not player_dialog.is_visible()

    context.close()


def test_codes_page(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{server_url}/codes.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    chips = page.locator("#codes-grid button")
    assert chips.count() > 0, "No code chips loaded"
    context.close()


def test_models_page(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{server_url}/models.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    models = page.locator("#models-grid a")
    assert models.count() > 0, "No models loaded"
    context.close()


def test_stats_page(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{server_url}/stats.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    bars = page.locator("#timeline-bars > div")
    assert bars.count() > 0, "No timeline bars rendered"
    context.close()


def test_sitemap_page(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{server_url}/sitemap.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    sitemap_rows = page.locator("#sitemap-list > div")
    assert sitemap_rows.count() > 0, "No sitemap rows rendered"
    context.close()


def test_mobile_responsiveness_and_overflow(server_url, browser_instance):
    context = browser_instance.new_context(viewport={"width": 375, "height": 667})
    page = context.new_page()
    page.goto(f"{server_url}/index.html")
    page.wait_for_load_state("networkidle")

    scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
    client_width = page.evaluate("() => document.documentElement.clientWidth")
    assert scroll_width <= client_width + 1, f"Horizontal overflow: {scroll_width} > {client_width}"
    context.close()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
