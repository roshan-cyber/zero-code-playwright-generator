"""Async Playwright service for DOM extraction and context building."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright


# In serverless Linux (Vercel), headless-shell binary may not be present.
# Force Playwright to use the regular Chromium binary when available.
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_USE_HEADLESS_SHELL", "0")


CHROMIUM_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
]


async def extract_dom_context(
    url: str,
    storage_state: Optional[Dict[str, Any]] = None,
    wait_until: str = "networkidle",
    timeout: int = 30000,
) -> str:
    """Navigate to URL, optionally inject storage_state, and return compressed DOM tree.

    Args:
        url: Target page URL to extract DOM from.
        storage_state: Optional Playwright storageState JSON (cookies + localStorage)
            to bypass login walls. Matches Playwright's native format:
            {"cookies": [...], "origins": [{"localStorage": [...]}]}.
        wait_until: Navigation wait condition (default: "networkidle").
        timeout: Navigation timeout in milliseconds (default: 30000).

    Returns:
        Compressed text representation of the interactive DOM tree.
        Each line format: `<tag#id.class [attrs...] role="..." data-testid="..." aria-label="...">  >>  "visible text"`
        Indentation reflects DOM nesting depth.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=CHROMIUM_LAUNCH_ARGS)
        context_kwargs = {}
        if storage_state:
            context_kwargs["storage_state"] = storage_state
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            await page.wait_for_load_state("domcontentloaded")

            dom_tree = await _build_compressed_dom(page)
            return dom_tree
        finally:
            await context.close()
            await browser.close()


async def _build_compressed_dom(page) -> str:
    """Return a compressed, line‑oriented DOM tree containing only clean,
    interactive form elements with their explicit native attributes.
    All scripts, styles, hidden inputs, SVG, and tracking attributes are removed.
    """
    script = r"""
    () => {
        const interactiveTags = new Set(['input','select','button','textarea','a']);
        const interactiveRoles = new Set(['button','link','tab','menuitem','checkbox','radio','textbox','combobox','listbox','searchbox','spinbutton','slider','switch']);

        const cssEscape = (value) => {
            try {
                return CSS.escape(value);
            } catch {
                return value.replace(/["\\]/g, '\\$&');
            }
        };

        const isVisible = (el) => {
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                return false;
            }
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        };

        const isInteractive = (el) => {
            if (!isVisible(el)) return false;
            const tag = el.tagName.toLowerCase();
            if (interactiveTags.has(tag)) return true;
            const role = el.getAttribute('role');
            if (role && interactiveRoles.has(role)) return true;
            if (el.hasAttribute('data-testid') || el.hasAttribute('data-test-id') || el.hasAttribute('data-cy') || el.hasAttribute('data-qa')) return true;
            return false;
        };

        const getVisibleText = (el) => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 200);

        const getLabelText = (el) => {
            if (!(el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement)) {
                return '';
            }
            if (el.labels && el.labels.length > 0) {
                return (el.labels[0].innerText || el.labels[0].textContent || '').trim().replace(/\s+/g, ' ');
            }
            if (el.id) {
                const explicit = document.querySelector(`label[for="${cssEscape(el.id)}"]`);
                if (explicit) return (explicit.innerText || explicit.textContent || '').trim().replace(/\s+/g, ' ');
            }
            return '';
        };

        const getAttributes = (el) => {
            const attrs = [];
            if (el.id) attrs.push(`#${el.id}`);
            if (el.name) attrs.push(`[name="${el.name.replace(/"/g,'\\"')}"]`);
            if (el.className && typeof el.className === 'string') {
                const classes = el.className.trim().split(/\s+/).filter(c => c);
                if (classes.length) attrs.push(`.${classes.join('.')}`);
            }
            const attrNames = ['placeholder', 'role', 'aria-label', 'aria-labelledby', 'for', 'autocomplete', 'type'];
            for (const attrName of attrNames) {
                const value = el.getAttribute(attrName);
                if (value) attrs.push(`[${attrName}="${value.replace(/"/g,'\\"')}"]`);
            }
            ['data-testid','data-test-id','data-cy','data-qa'].forEach(a => {
                const v = el.getAttribute(a);
                if (v) attrs.push(`[${a}="${v.replace(/"/g,'\\"')}"]`);
            });
            const labelText = getLabelText(el);
            if (labelText) attrs.push(`[label="${labelText.replace(/"/g,'\\"')}"]`);
            return attrs.join(' ');
        };

        const nodes = Array.from(document.querySelectorAll('*'));
        const lines = [];
        for (const current of nodes) {
            if (!isInteractive(current)) continue;
            const tag = current.tagName.toLowerCase();
            const attrs = getAttributes(current);
            const text = getVisibleText(current);
            lines.push(`<${tag}${attrs ? ' ' + attrs : ''}>  >>  "${text}"`);
        }
        return lines.join('\n');
    }
    """
    return await page.evaluate(script)


async def _clean_html(html: str) -> str:
    """Clean and minimize HTML for LLM context."""
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style\b[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<meta\b[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
    return html.strip()


async def extract_authenticated_dom(
    login_url: str,
    username: str,
    password: str,
    target_url: str,
    wait_until: str = "networkidle",
    timeout: int = 60000,
) -> str:
    """
    Perform automated login then navigate to target_url and return compressed DOM.

    Steps:
    1. Launch headless browser.
    2. Go to login_url, wait for network idle.
    3. Click the SSO button (id=adLoginLogo) to redirect to IdP.
    4. Wait for username/password fields on IdP, fill them.
    5. Submit credentials (avoid original SSO button).
    6. Wait for network idle, then navigate to target_url.
    7. Return compressed interactive DOM via _build_compressed_dom.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=CHROMIUM_LAUNCH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Navigate to login page
            await page.goto(login_url, wait_until=wait_until, timeout=timeout)
            await page.wait_for_load_state("domcontentloaded")

            # 2. Click the SSO button (id=adLoginLogo) to redirect to IdP
            sso_button = page.locator('#adLoginLogo')
            if await sso_button.count():
                await sso_button.first.click()
                await page.wait_for_load_state("networkidle", timeout=timeout)
            else:
                pass

            # 3. Fill username on IdP page
            username_filled = False
            username_selectors = [
                'input[type="email"]',
                'input[name*="user" i]',
                'input[id*="user" i]',
                'input[name*="email" i]',
                'input[id*="email" i]',
                'input[autocomplete="username"]',
                'input[type="text"]',
            ]
            for selector in username_selectors:
                loc = page.locator(selector)
                try:
                    await loc.first.wait_for(state="visible", timeout=15000)
                    await loc.first.fill(username)
                    username_filled = True
                    break
                except Exception:
                    continue
            if not username_filled:
                raise RuntimeError("Unable to locate username field after SSO redirect")

            # 4. Fill password
            password_filled = False
            password_selectors = [
                'input[type="password"]',
                'input[name*="pass" i]',
                'input[id*="pass" i]',
                'input[autocomplete="current-password"]',
            ]
            for selector in password_selectors:
                loc = page.locator(selector)
                try:
                    await loc.first.wait_for(state="visible", timeout=10000)
                    await loc.first.fill(password)
                    password_filled = True
                    break
                except Exception:
                    continue
            if not password_filled:
                raise RuntimeError("Unable to locate password field after SSO redirect")

            # 5. Submit credentials (avoid original SSO button)
            submit_clicked = False
            submit_selectors = [
                'button:has-text("Sign in")',
                'button:has-text("Sign In")',
                'button:has-text("Login")',
                'button:has-text("Submit")',
                'input[type="submit"]',
                'button[type="submit"]',
            ]
            for selector in submit_selectors:
                loc = page.locator(selector)
                count = await loc.count()
                if count:
                    for i in range(count):
                        element = loc.nth(i)
                        elem_id = await element.get_attribute('id')
                        if elem_id == 'adLoginLogo':
                            continue
                        try:
                            await element.wait_for(state="visible", timeout=5000)
                            await element.click()
                            submit_clicked = True
                            break
                        except Exception:
                            continue
                if submit_clicked:
                    break
            if not submit_clicked:
                await page.keyboard.press("Enter")

            # 6. Wait for post-login navigation
            await page.wait_for_load_state("networkidle", timeout=timeout)

            # 7. Navigate to target_url
            await page.goto(target_url, wait_until=wait_until, timeout=timeout)
            await page.wait_for_load_state("domcontentloaded")

            # 8. Extract compressed DOM
            dom_tree = await _build_compressed_dom(page)
            return dom_tree
        except Exception as e:
            print(f"[extract_authenticated_dom] ERROR: {e}")
            raise
        finally:
            await context.close()
            await browser.close()


async def create_session(
    login_url: str,
    username: str,
    password: str,
    wait_until: str = "networkidle",
    timeout: int = 60000,
) -> bool:
    """
    Perform automated login only and verify that authentication succeeds.
    Returns True if login completes without timeout/error.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=CHROMIUM_LAUNCH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Navigate to login page
            await page.goto(login_url, wait_until=wait_until, timeout=timeout)
            await page.wait_for_load_state("domcontentloaded")

            # 2. Click the SSO button (id=adLoginLogo) to redirect to IdP
            sso_button = page.locator('#adLoginLogo')
            if await sso_button.count():
                # Click and wait for navigation to the identity provider page
                await sso_button.first.click()
                # Wait for navigation and network idle on the IdP page
                await page.wait_for_load_state("networkidle", timeout=timeout)
            else:
                # If the button is not present, continue; maybe the form is already visible
                pass

            # 3. Wait for username field to appear on the IdP page
            username_filled = False
            username_selectors = [
                'input[type="email"]',
                'input[name*="user" i]',
                'input[id*="user" i]',
                'input[name*="email" i]',
                'input[id*="email" i]',
                'input[autocomplete="username"]',
                'input[type="text"]',
            ]
            for selector in username_selectors:
                loc = page.locator(selector)
                try:
                    await loc.first.wait_for(state="visible", timeout=15000)
                    await loc.first.fill(username)
                    username_filled = True
                    break
                except Exception:
                    continue
            if not username_filled:
                raise RuntimeError("Unable to locate username field after SSO redirect")

            # 4. Fill password
            password_filled = False
            password_selectors = [
                'input[type="password"]',
                'input[name*="pass" i]',
                'input[id*="pass" i]',
                'input[autocomplete="current-password"]',
            ]
            for selector in password_selectors:
                loc = page.locator(selector)
                try:
                    await loc.first.wait_for(state="visible", timeout=10000)
                    await loc.first.fill(password)
                    password_filled = True
                    break
                except Exception:
                    continue
            if not password_filled:
                raise RuntimeError("Unable to locate password field after SSO redirect")

            # 5. Submit – click the credential submit button (avoid the original SSO button)
            submit_clicked = False
            submit_selectors = [
                'button:has-text("Sign in")',
                'button:has-text("Sign In")',
                'button:has-text("Login")',
                'button:has-text("Submit")',
                'input[type="submit"]',
                'button[type="submit"]',
            ]
            for selector in submit_selectors:
                loc = page.locator(selector)
                count = await loc.count()
                if count:
                    for i in range(count):
                        element = loc.nth(i)
                        elem_id = await element.get_attribute('id')
                        if elem_id == 'adLoginLogo':
                            continue
                        # Ensure button is visible/enabled
                        try:
                            await element.wait_for(state="visible", timeout=5000)
                            await element.click()
                            submit_clicked = True
                            break
                        except Exception:
                            continue
                if submit_clicked:
                    break
            if not submit_clicked:
                # Fallback: press Enter on password field
                await page.keyboard.press("Enter")

            # 6. Wait for navigation / network idle after credential submit
            await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            # Log for debugging (will appear in uvicorn console)
            print(f"[create_session] ERROR: {e}")
            return False
        finally:
            await context.close()
            await browser.close()


async def _build_lightweight_dom(page) -> str:
    """Return a minimal DOM snapshot containing only interactive elements with
    selector‑relevant attributes (id, data‑testid, role, name, placeholder, text)."""
    script = r"""
    () => {
        const interactiveSelectors = [
            'a','button','input','select','textarea',
            '[role="button"]','[role="link"]','[role="textbox"]',
            '[role="checkbox"]','[role="radio"]','[role="menuitem"]',
            '[role="tab"]','[role="option"]','[role="combobox"]',
            '[role="listbox"]','[role="searchbox"]','[role="spinbutton"]',
            '[role="slider"]','[role="switch"]','[contenteditable="true"]',
            '[data-testid]','[data-test-id]','[data-cy]','[data-qa]'
        ];

        const isVisible = (el) => {
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                return false;
            }
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        };

        const isInteractive = (el) => {
            if (!isVisible(el)) return false;
            if (interactiveSelectors.some(s => el.matches(s))) return true;
            const role = el.getAttribute('role');
            if (role && ['button','link','textbox','checkbox','radio','menuitem',
                         'tab','option','combobox','listbox','searchbox',
                         'spinbutton','slider','switch'].includes(role)) {
                return true;
            }
            return false;
        };

        const getVisibleText = (el) => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0,200);

        const getAttrs = (el) => {
            const attrs = [];
            if (el.id) attrs.push(`#${el.id}`);
            const important = ['data-testid','data-test-id','data-cy','data-qa','role','name','placeholder','type','aria-label','aria-labelledby'];
            for (const a of important) {
                const v = el.getAttribute(a);
                if (v) attrs.push(`[${a}="${v.replace(/"/g,'\\"')}"]`);
            }
            return attrs.join(' ');
        };

        const lines = [];
        for (const current of Array.from(document.querySelectorAll('*'))) {
            if (!isInteractive(current)) continue;
            const tag = current.tagName.toLowerCase();
            const attrs = getAttrs(current);
            const text = getVisibleText(current);
            lines.push(`<${tag}${attrs ? ' ' + attrs : ''}>  >>  "${text}"`);
        }
        return lines.join('\n');
    }
    """
    return await page.evaluate(script)


async def extract_dom_with_pre_action(
    target_url: str,
    pre_action: str,
    get_selector,
    wait_until: str = "networkidle",
    timeout: int = 60000,
) -> str:
    """
    Two‑pass navigation:
    1. Load target_url, capture a lightweight DOM.
    2. Ask the LLM (via get_selector) for the selector that fulfills `pre_action`.
    3. Click that selector, wait for network idle.
    4. Return the full compressed DOM of the resulting view.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=CHROMIUM_LAUNCH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Navigate to the page
            await page.goto(target_url, wait_until=wait_until, timeout=timeout)
            await page.wait_for_load_state("domcontentloaded")

            # 2. Lightweight snapshot
            lightweight_dom = await _build_lightweight_dom(page)

            # 3. Ask LLM for selector
            selector = await get_selector(pre_action, lightweight_dom)
            selector = selector.strip()
            if not selector:
                raise RuntimeError("LLM returned empty selector")

            # 4. Perform the click
            await page.locator(selector).first.click()
            await page.wait_for_load_state("networkidle", timeout=timeout)

            # 5. Full DOM after interaction
            full_dom = await _build_compressed_dom(page)
            return full_dom
        finally:
            await context.close()
            await browser.close()