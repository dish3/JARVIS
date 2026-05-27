#!/usr/bin/env python3
"""
LinkedIn Tool - Post, delete, and manage LinkedIn content via Playwright.
Improvements over previous version:
  - _click_with_retry()  : retries each selector up to 3 times before moving on
  - _is_session_expired(): detects login/authwall/session-expired pages
  - _screenshot()        : always saves on failure with a timestamped name
  - Clear [LINKEDIN] log tags at every step
  - Posting workflow preserved exactly
"""

import os
import logging
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

env_path = Path("E:/PROJECTS/JARVIS/VirtualAssistant/.env")
load_dotenv(dotenv_path=env_path, override=True)
logger = logging.getLogger('LINKEDIN_TOOL')

SESSION_FILE    = Path("E:/PROJECTS/JARVIS/VirtualAssistant/linkedin_session.json")
SCREENSHOT_DIR  = Path("E:/PROJECTS/JARVIS/generated_images")
SELECTOR_RETRIES = 3          # how many times to retry each selector
SELECTOR_WAIT    = 3000       # ms to wait for each selector attempt


class LinkedInTool:

    def __init__(self):
        logger.info("Initializing LinkedIn Tool...")
        logger.info("[OK] LinkedIn Tool initialized")

    # ── Public API ─────────────────────────────────────────────────────────────

    def post(self, text: str, image_path: str = None) -> str:
        from playwright.sync_api import sync_playwright

        email    = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')

        if not email or 'example.com' in email:
            return f"Error: LinkedIn credentials not set. Email found: '{email}'"

        logger.info("[LINKEDIN] Starting post workflow...")

        with sync_playwright() as p:
            browser, page = self._open_linkedin_page(p)
            if isinstance(browser, str):
                return browser  # navigation error string

            # Detect expired / missing session
            if self._is_session_expired(page):
                logger.info("[LINKEDIN] Session expired or not logged in — re-logging in")
                context = browser.contexts[0]
                if not self._login(page, email, password):
                    self._screenshot(page, 'login_failed')
                    browser.close()
                    return "Error: LinkedIn login failed. Check linkedin_login_failed_*.png"
                context.storage_state(path=str(SESSION_FILE))
                logger.info("[LINKEDIN] Session saved after fresh login")

            result = self._create_post(page, text, image_path)
            browser.close()
            return result

    def delete_last_post(self) -> str:
        from playwright.sync_api import sync_playwright

        email = os.getenv('LINKEDIN_EMAIL')
        if not email or 'example.com' in email:
            return f"Error: LinkedIn credentials not set. Email found: '{email}'"

        logger.info("[LINKEDIN] Starting delete-last-post workflow...")

        with sync_playwright() as p:
            browser, page = self._open_linkedin_page(p)
            if isinstance(browser, str):
                return browser

            if self._is_session_expired(page):
                self._screenshot(page, 'session_expired')
                browser.close()
                return "Error: LinkedIn session expired. Re-run to trigger fresh login."

            return self._delete_most_recent_post(page, browser)

    # ── Session helpers ────────────────────────────────────────────────────────

    def _is_session_expired(self, page) -> bool:
        """
        Return True if the current page indicates the session is gone.
        Checks URL for login/authwall/session-expired and page content
        for the sign-in form.
        """
        url = page.url.lower()
        expired_signals = ('login', 'authwall', 'session-expired', 'uas/authenticate')
        if any(s in url for s in expired_signals):
            logger.warning(f"[LINKEDIN] Session expired — URL: {page.url}")
            return True

        # Also check if the sign-in form is visible on the page
        try:
            if page.locator('#username').is_visible(timeout=1500):
                logger.warning("[LINKEDIN] Session expired — login form visible on page")
                return True
        except Exception:
            pass

        return False

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _open_linkedin_page(self, p):
        """
        Launch browser, restore session if available, navigate to feed.
        Returns (browser, page) on success or (error_str, None) on failure.
        """
        browser = p.chromium.launch(headless=False)

        if SESSION_FILE.exists():
            context = browser.new_context(storage_state=str(SESSION_FILE))
            logger.info("[LINKEDIN] Loaded saved session from disk")
        else:
            context = browser.new_context()
            logger.info("[LINKEDIN] No saved session — starting fresh context")

        page = context.new_page()

        for attempt in range(1, 4):
            try:
                logger.info(f"[LINKEDIN] Navigating to feed (attempt {attempt}/3)...")
                page.goto(
                    "https://www.linkedin.com/feed/",
                    wait_until="domcontentloaded",
                    timeout=90000,
                )
                logger.info(f"[LINKEDIN] Feed loaded — URL: {page.url}")
                break
            except Exception as nav_err:
                logger.warning(f"[LINKEDIN] Navigation attempt {attempt} failed: {nav_err}")
                if attempt == 3:
                    browser.close()
                    return f"Error: Could not load LinkedIn after 3 attempts: {nav_err}", None
                time.sleep(5)

        time.sleep(5)
        return browser, page

    def _login(self, page, email: str, password: str) -> bool:
        """Fill login form and verify redirect to feed."""
        try:
            logger.info("[LINKEDIN] Navigating to login page...")
            page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=90000,
            )
            time.sleep(2)
            page.fill('#username', email)
            page.fill('#password', password)
            page.click('button[type="submit"]')
            time.sleep(4)
            if "feed" in page.url or "checkpoint" in page.url:
                logger.info("[LINKEDIN] Login successful")
                return True
            logger.error(f"[LINKEDIN] Login failed — landed on: {page.url}")
            return False
        except Exception as e:
            logger.error(f"[LINKEDIN] Login error: {e}")
            return False

    # ── Core: create post ──────────────────────────────────────────────────────

    def _create_post(self, page, text: str, image_path: str = None) -> str:
        """
        Full posting workflow — preserved from previous version.
        Every selector group now uses _click_with_retry() for 3-attempt resilience.
        """
        try:
            logger.info("[LINKEDIN] Starting _create_post...")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)

            # ── Step 1: click "Start a post" ──────────────────────────────────
            logger.info("[LINKEDIN] Step 1: clicking 'Start a post'...")
            start_post_selectors = [
                'div.share-box-feed-entry__trigger',
                '[placeholder="Start a post"]',
                'button:has-text("Start a post")',
                'div.share-box-feed-entry__top-bar',
            ]
            clicked = self._click_with_retry(page, start_post_selectors, label="Start a post")

            if not clicked:
                # Last-resort: get_by_text (Playwright locator, not CSS)
                try:
                    page.get_by_text("Start a post", exact=True).first.click(timeout=5000)
                    clicked = True
                    logger.info("[LINKEDIN] Clicked 'Start a post' via get_by_text fallback")
                except Exception:
                    pass

            if not clicked:
                self._screenshot(page, 'start_post_not_found')
                return "Error: Could not find 'Start a post' button. Check screenshot."

            # ── Step 2: wait for post dialog ──────────────────────────────────
            logger.info("[LINKEDIN] Step 2: waiting for post dialog...")
            time.sleep(6)
            try:
                page.wait_for_selector('div[role="dialog"]', timeout=10000)
                logger.info("[LINKEDIN] Post dialog confirmed open")
            except Exception:
                logger.warning("[LINKEDIN] dialog[role=dialog] not found — continuing anyway")
            time.sleep(2)

            self._screenshot(page, 'dialog_opened')

            # ── Step 3: find and fill textbox ─────────────────────────────────
            logger.info("[LINKEDIN] Step 3: locating text area...")
            textbox_selectors = [
                'div[role="textbox"]',
                '.ql-editor',
                'div.editor-content',
                '[data-placeholder="What do you want to talk about?"]',
                'div.share-creation-state__text-editor div[contenteditable="true"]',
                'div[contenteditable="true"]',
            ]
            textbox = self._find_visible(page, textbox_selectors, label="textbox")

            if not textbox:
                self._screenshot(page, 'textbox_not_found')
                return "Error: Could not find post text area. Check screenshot."

            textbox.click()
            textbox.type(text, delay=50)
            logger.info(f"[LINKEDIN] Typed post text ({len(text)} chars)")
            time.sleep(2)

            # ── Step 4: upload image (optional) ───────────────────────────────
            if image_path:
                self._upload_image(page, image_path)

            # ── Step 5: preview screenshot ────────────────────────────────────
            preview_path = str(SCREENSHOT_DIR / "linkedin_preview.png")
            page.screenshot(path=preview_path)
            logger.info(f"[LINKEDIN] Preview screenshot saved: {preview_path}")

            # ── Step 6: click Post button ─────────────────────────────────────
            logger.info("[LINKEDIN] Step 6: clicking Post button...")
            post_selectors = [
                'button.share-actions__primary-action',
                'button[aria-label="Post"]',
                'button[aria-label*="Post"]',
                'div[role="dialog"] button:has-text("Post")',
                'button:has-text("Post")',
                '[data-control-name="share.post"]',
                'button.artdeco-button--primary:has-text("Post")',
            ]
            posted = self._click_with_retry(page, post_selectors, label="Post button")

            if not posted:
                # Last resort: any primary button in the dialog
                try:
                    btns = page.locator('div[role="dialog"] button.artdeco-button--primary')
                    count = btns.count()
                    logger.info(f"[LINKEDIN] Found {count} primary buttons in dialog")
                    if count > 0:
                        btns.last.click()
                        posted = True
                        logger.info("[LINKEDIN] Posted via last primary button fallback")
                except Exception:
                    pass

            if not posted:
                self._screenshot(page, 'post_button_not_found')
                return f"Error: Could not click Post button. Preview saved: {preview_path}"

            time.sleep(3)
            logger.info("[LINKEDIN] Post submitted successfully")
            return f"Posted to LinkedIn! Preview: {preview_path}"

        except Exception as e:
            logger.error(f"[LINKEDIN] _create_post error: {e}")
            self._screenshot(page, 'create_post_error')
            return f"Error posting: {str(e)}"

    # ── Core: delete post ──────────────────────────────────────────────────────

    def _delete_most_recent_post(self, page, browser) -> str:
        """Navigate to profile, open three-dot menu, delete most recent post."""
        try:
            logger.info("[LINKEDIN] Navigating to profile...")
            page.goto(
                "https://www.linkedin.com/in/me/",
                wait_until="domcontentloaded",
                timeout=90000,
            )
            time.sleep(4)
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(3)

            self._screenshot(page, 'profile_loaded')

            # ── Step 1: open three-dot menu ───────────────────────────────────
            logger.info("[LINKEDIN] Step 1: finding three-dot menu...")
            three_dot_selectors = [
                'button[aria-label*="Open control menu"]',
                'button[aria-label*="control menu"]',
                'button[aria-label*="More options"]',
                'button[aria-label*="more options"]',
                '.feed-shared-control-menu__trigger',
            ]
            clicked = self._click_with_retry(page, three_dot_selectors, label="three-dot menu")

            if not clicked:
                self._screenshot(page, 'three_dot_not_found')
                browser.close()
                return "Error: Could not find post menu button. Check screenshot."

            time.sleep(3)
            self._screenshot(page, 'dropdown_open')

            # ── Step 2: click Delete ──────────────────────────────────────────
            logger.info("[LINKEDIN] Step 2: clicking Delete in dropdown...")
            delete_selectors = [
                'a[role="menuitem"]:has-text("Delete post")',
                'div[role="menuitem"]:has-text("Delete post")',
                '[role="menuitem"]:has-text("Delete post")',
                '[role="menuitem"]:has-text("Delete")',
            ]
            deleted = self._click_with_retry(page, delete_selectors, label="Delete menu item")

            if not deleted:
                self._screenshot(page, 'delete_option_not_found')
                browser.close()
                return "Error: Could not find Delete option in menu. Check screenshot."

            time.sleep(2)

            # ── Step 3: confirm deletion ──────────────────────────────────────
            logger.info("[LINKEDIN] Step 3: confirming deletion...")
            confirm_selectors = [
                'div[role="dialog"] button:has-text("Delete")',
                'button.artdeco-button--primary:has-text("Delete")',
                'button[aria-label*="Delete"]',
                'button:has-text("Delete")',
            ]
            confirmed = self._click_with_retry(
                page, confirm_selectors, label="Delete confirm button", wait_ms=4000
            )

            time.sleep(3)
            self._screenshot(page, 'after_delete')
            browser.close()

            if confirmed:
                logger.info("[LINKEDIN] Post deleted successfully")
                return "Deleted most recent LinkedIn post successfully."
            return (
                "Delete clicked but confirmation not found — "
                "post may still be deleted. Check screenshot."
            )

        except Exception as e:
            logger.error(f"[LINKEDIN] _delete_most_recent_post error: {e}")
            self._screenshot(page, 'delete_error')
            try:
                browser.close()
            except Exception:
                pass
            return f"Error deleting post: {str(e)}"

    # ── Image upload ───────────────────────────────────────────────────────────

    def _upload_image(self, page, image_path: str) -> None:
        """
        Upload an image using Playwright's file-chooser interception.
        Falls back to direct set_input_files if the chooser times out.
        """
        logger.info(f"[LINKEDIN] Uploading image: {image_path}")

        if not Path(image_path).exists():
            logger.warning(f"[LINKEDIN] Image file not found — skipping: {image_path}")
            return

        photo_selectors = [
            'button[aria-label*="media"]',
            'button[aria-label="Add a photo"]',
            'button[aria-label*="photo"]',
            'button[aria-label*="Photo"]',
            'button[aria-label*="image"]',
            'button:has-text("Photo")',
            'button:has-text("Add a photo")',
        ]

        try:
            with page.expect_file_chooser(timeout=8000) as fc_info:
                clicked = self._click_with_retry(
                    page, photo_selectors, label="photo button"
                )
                if not clicked:
                    logger.warning("[LINKEDIN] Photo button not found — skipping image upload")
                    return

            fc_info.value.set_files(image_path)
            logger.info("[LINKEDIN] Image set via file chooser")
            time.sleep(6)
            logger.info("[LINKEDIN] Image upload complete")

        except Exception as img_err:
            logger.warning(f"[LINKEDIN] File chooser failed: {img_err} — trying direct input")
            try:
                page.set_input_files('input[type="file"]', image_path)
                logger.info("[LINKEDIN] Image uploaded via direct file input (fallback)")
                time.sleep(6)
            except Exception as fb_err:
                logger.warning(f"[LINKEDIN] Direct file input also failed: {fb_err}")

    # ── Shared utilities ───────────────────────────────────────────────────────

    def _click_with_retry(
        self,
        page,
        selectors: list,
        label: str = "element",
        retries: int = SELECTOR_RETRIES,
        wait_ms: int = SELECTOR_WAIT,
    ) -> bool:
        """
        Try each selector up to `retries` times.
        Logs every attempt and outcome with [LINKEDIN] tags.
        Returns True as soon as one click succeeds, False if all fail.
        """
        for selector in selectors:
            for attempt in range(1, retries + 1):
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=wait_ms):
                        el.click()
                        logger.info(
                            f"[LINKEDIN] Clicked {label} "
                            f"via '{selector}' (attempt {attempt}/{retries})"
                        )
                        return True
                    else:
                        logger.debug(
                            f"[LINKEDIN] {label} not visible: '{selector}' "
                            f"(attempt {attempt}/{retries})"
                        )
                except Exception as e:
                    logger.debug(
                        f"[LINKEDIN] {label} selector error: '{selector}' "
                        f"attempt {attempt}/{retries} — {e}"
                    )
                if attempt < retries:
                    time.sleep(0.5)

        logger.warning(f"[LINKEDIN] Could not click {label} — all selectors exhausted")
        return False

    def _find_visible(self, page, selectors: list, label: str = "element"):
        """
        Return the first visible Playwright locator from the list, or None.
        Tries each selector once (no retry needed for find — only for click).
        """
        for selector in selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=SELECTOR_WAIT):
                    logger.info(f"[LINKEDIN] Found {label}: '{selector}'")
                    return el
            except Exception:
                continue
        logger.warning(f"[LINKEDIN] Could not find {label} — all selectors tried")
        return None

    def _screenshot(self, page, tag: str) -> str:
        """
        Save a timestamped screenshot to SCREENSHOT_DIR.
        Always called on failure so there is always a visual record.
        Returns the saved path string.
        """
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(SCREENSHOT_DIR / f"linkedin_{tag}_{ts}.png")
        try:
            page.screenshot(path=path)
            logger.info(f"[LINKEDIN] Screenshot saved: {path}")
        except Exception as e:
            logger.warning(f"[LINKEDIN] Could not save screenshot: {e}")
        return path
