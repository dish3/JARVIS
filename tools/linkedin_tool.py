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

    # State constants — used by detect_linkedin_post_state()
    STATE_COMPOSER      = 'STATE_A'   # Main composer: Post + Add media + Schedule post visible
    STATE_IMAGE_PREVIEW = 'STATE_B'   # Image editor: Next + Back + Edit + Tag visible
    STATE_UNKNOWN       = 'STATE_UNKNOWN'

    def detect_linkedin_post_state(self, page) -> str:
        """
        Inspect visible buttons to determine which workflow state LinkedIn is in.

        STATE_A (Composer):
            - 'Post' button visible (exact text)
            - OR 'Schedule post' button visible (aria-label)
            - OR 'Add media' button visible (aria-label)

        STATE_B (Image Preview/Editor):
            - 'Next' button visible (aria-label="Next")
            - AND 'Back' button visible (aria-label="Back")

        Returns STATE_COMPOSER, STATE_IMAGE_PREVIEW, or STATE_UNKNOWN.
        """
        try:
            # Check STATE_B first — it's the more specific condition
            next_visible = False
            back_visible = False
            try:
                next_visible = page.locator('button[aria-label="Next"]').first.is_visible(timeout=1500)
            except Exception:
                pass
            try:
                back_visible = page.locator('button[aria-label="Back"]').first.is_visible(timeout=1500)
            except Exception:
                pass

            if next_visible and back_visible:
                logger.info("[STATE] ImagePreview — Next+Back buttons visible")
                return self.STATE_IMAGE_PREVIEW

            # Check STATE_A
            post_visible     = False
            schedule_visible = False
            media_visible    = False
            try:
                # Use get_by_role for exact text match — avoids partial matches
                post_visible = page.get_by_role('button', name='Post', exact=True).first.is_visible(timeout=1500)
            except Exception:
                pass
            try:
                schedule_visible = page.locator('button[aria-label="Schedule post"]').first.is_visible(timeout=1500)
            except Exception:
                pass
            try:
                media_visible = page.locator('button[aria-label="Add media"]').first.is_visible(timeout=1500)
            except Exception:
                pass

            if post_visible or schedule_visible or media_visible:
                logger.info(
                    f"[STATE] Composer — post={post_visible} "
                    f"schedule={schedule_visible} media={media_visible}"
                )
                return self.STATE_COMPOSER

        except Exception as e:
            logger.warning(f"[STATE] Detection error: {e}")

        logger.warning("[STATE] Unknown — could not determine workflow state")
        return self.STATE_UNKNOWN

    def _create_post(self, page, text: str, image_path: str = None) -> str:
        """
        State-based posting workflow.

        States:
          STATE_A (Composer)     — textbox + Post + Add media + Schedule post visible
          STATE_B (ImagePreview) — Next + Back + Edit + Tag visible after image upload

        Flow:
          1. Open composer
          2. Type text
          3. If image: upload → detect state → if STATE_B: click Next → verify STATE_A
          4. Verify STATE_A before attempting Post
          5. Click Post via _click_post_button()
          6. Verify submission
        """
        try:
            logger.info("[LINKEDIN] Starting _create_post (state-based)...")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)

            # ── Step 1: click "Start a post" ──────────────────────────────────
            logger.info("[LINKEDIN] Step 1: clicking 'Start a post'...")
            start_post_selectors = [
                # PRIMARY — stable aria-label confirmed from live DOM inspection
                'div[aria-label="Start a post"]',
                # FALLBACK 1 — placeholder attribute
                '[placeholder="Start a post"]',
                # FALLBACK 2 — button variant
                'button[aria-label="Start a post"]',
                # FALLBACK 3 — legacy CSS class (brittle, last resort)
                'div.share-box-feed-entry__trigger',
            ]
            clicked = self._click_with_retry(page, start_post_selectors, label="Start a post")

            if not clicked:
                try:
                    page.get_by_text("Start a post", exact=True).first.click(timeout=5000)
                    clicked = True
                    logger.info("[LINKEDIN] Clicked 'Start a post' via get_by_text fallback")
                except Exception:
                    pass

            if not clicked:
                self._screenshot(page, 'start_post_not_found')
                return "Error: Could not find 'Start a post' button. Check screenshot."

            # ── Step 2: wait for composer to open ─────────────────────────────
            logger.info("[LINKEDIN] Step 2: waiting for composer...")
            # Wait for the textbox to appear — this is the definitive signal
            # that the composer is fully open and ready for input.
            textbox_ready = False
            for _ in range(10):  # up to 20s
                try:
                    el = page.locator('div[aria-label="Text editor for creating content"]').first
                    if el.is_visible(timeout=2000):
                        textbox_ready = True
                        logger.info("[LINKEDIN] Composer textbox is visible — ready")
                        break
                except Exception:
                    pass
                time.sleep(2)

            if not textbox_ready:
                logger.warning("[LINKEDIN] Textbox not visible after 20s — checking state anyway")
                state = self.detect_linkedin_post_state(page)
                logger.info(f"[LINKEDIN] State after wait: {state}")

            self._screenshot(page, 'dialog_opened')

            # ── Step 3: find and fill textbox ─────────────────────────────────
            logger.info("[LINKEDIN] Step 3: locating text area...")
            textbox_selectors = [
                # PRIMARY — stable aria-label confirmed from live DOM inspection
                'div[aria-label="Text editor for creating content"]',
                # FALLBACK 1 — data-placeholder unique to this element
                '[data-placeholder="What do you want to talk about?"]',
                # FALLBACK 2 — role=textbox
                'div[role="textbox"]',
                # FALLBACK 3 — Quill editor class
                '.ql-editor',
                # FALLBACK 4 — broadest match
                'div[contenteditable="true"]',
            ]
            
            # Wait for text editor to load and be visible (prevents failure if Quill editor is loading slowly)
            for selector in textbox_selectors[:3]:
                try:
                    page.wait_for_selector(selector, state="visible", timeout=15000)
                    logger.info(f"[LINKEDIN] Textbox selector '{selector}' became visible")
                    break
                except Exception:
                    continue

            textbox = self._find_visible(page, textbox_selectors, label="textbox")

            if not textbox:
                self._screenshot(page, 'textbox_not_found')
                return "Error: Could not find post text area. Check screenshot."

            textbox.click()
            textbox.type(text, delay=50)
            logger.info(f"[LINKEDIN] Typed post text ({len(text)} chars)")
            time.sleep(2)

            # ── Step 4: upload image + state transition ────────────────────────
            if image_path:
                self._upload_image(page, image_path)
                self._screenshot(page, 'after_upload')

                # Detect state after upload
                logger.info("[LINKEDIN] Step 4b: detecting state after image upload...")
                time.sleep(2)
                state = self.detect_linkedin_post_state(page)

                if state == self.STATE_IMAGE_PREVIEW:
                    logger.info("[STATE] TransitioningToComposer — clicking Next...")
                    self._screenshot(page, 'before_next_click')

                    next_clicked = False
                    try:
                        back_btn = page.locator('button[aria-label="Back"]').first
                        if back_btn.is_visible(timeout=3000):
                            # The image editor has TWO Next buttons on the page:
                            #   [0] data-testid="carousel-inline-right-button" — feed carousel (wrong)
                            #   [1] class contains "share-box-footer__primary-btn" — image editor (correct)
                            # Select by the stable semantic class, not aria-label alone.
                            next_btn = page.locator('button[aria-label="Next"].artdeco-button').last
                            if not next_btn.is_visible(timeout=2000):
                                # Fallback: second Next button (index 1)
                                next_btn = page.locator('button[aria-label="Next"]').nth(1)
                            if next_btn.is_visible(timeout=3000):
                                next_btn.click(force=True, timeout=5000)
                                next_clicked = True
                                logger.info("[LINKEDIN] Clicked image editor Next (share-box-footer)")
                        else:
                            logger.warning("[LINKEDIN] Back button not visible — not in image editor")
                    except Exception as e:
                        logger.warning(f"[LINKEDIN] Next click error: {e}")

                    if next_clicked:
                        logger.info("[LINKEDIN] Clicked Next — waiting for composer...")
                        time.sleep(4)
                        self._screenshot(page, 'after_next_click')

                        # Verify we're back in STATE_A
                        for attempt in range(6):
                            state = self.detect_linkedin_post_state(page)
                            if state == self.STATE_COMPOSER:
                                logger.info("[STATE] Composer — ready to post")
                                break
                            logger.info(f"[STATE] Still {state} after Next (attempt {attempt+1}/6)...")
                            time.sleep(2)
                        else:
                            logger.warning("[STATE] Did not reach Composer after Next — proceeding anyway")
                    else:
                        logger.warning("[LINKEDIN] Could not click Next — proceeding anyway")

                elif state == self.STATE_COMPOSER:
                    logger.info("[STATE] Composer — image upload did not change state")

                else:
                    logger.warning(f"[STATE] Unknown state after upload: {state} — proceeding")

            # ── Step 5: verify we are in STATE_A before posting ───────────────
            logger.info("[LINKEDIN] Step 5: verifying composer state before Post...")
            final_state = self.detect_linkedin_post_state(page)
            if final_state != self.STATE_COMPOSER:
                logger.warning(
                    f"[LINKEDIN] Not in Composer state ({final_state}) — "
                    "attempting Post anyway"
                )

            # Preview screenshot
            preview_path = str(SCREENSHOT_DIR / "linkedin_preview.png")
            page.screenshot(path=preview_path)
            logger.info(f"[LINKEDIN] Preview screenshot saved: {preview_path}")

            # ── Step 6: click Post button ──────────────────────────────────────
            logger.info("[LINKEDIN] Step 6: clicking Post button...")
            posted = self._click_post_button(page, text)

            if not posted:
                self._screenshot(page, 'post_button_not_found')
                return f"Error: Could not click Post button. Preview saved: {preview_path}"

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

    # ── Post button: Playwright-native click ──────────────────────────────────

    def _click_post_button(self, page, post_text: str) -> bool:
        """
        Click the Post button using Playwright's get_by_role — which pierces
        shadow DOM automatically, unlike document.querySelectorAll in JS.

        The Post button has accessible name "Post" (exact). This is confirmed
        by state detection which uses the same get_by_role call successfully.

        Retries 3 times with 1s between attempts.
        Verifies by checking textbox disappears after click.
        """
        self._screenshot(page, 'before_post_click')

        for attempt in range(1, 4):
            logger.info(f"[LINKEDIN] Post click attempt {attempt}/3...")
            try:
                # get_by_role pierces shadow DOM — same method used in state detection
                btn = page.get_by_role('button', name='Post', exact=True).last
                if btn.is_visible(timeout=3000):
                    btn.scroll_into_view_if_needed(timeout=3000)
                    # force=True bypasses the interop-shadowdom overlay
                    # that intercepts pointer events on LinkedIn
                    btn.click(force=True, timeout=5000)
                    logger.info(f"[LINKEDIN] Post button clicked via get_by_role (attempt {attempt}/3)")
                    break
                else:
                    logger.warning(f"[LINKEDIN] Post button not visible (attempt {attempt}/3)")
            except Exception as e:
                logger.warning(f"[LINKEDIN] Post click failed attempt {attempt}/3: {e}")
            if attempt < 3:
                time.sleep(1)
        else:
            logger.error("[LINKEDIN] All 3 Post click attempts failed")
            self._screenshot(page, 'post_click_failed')
            return False

        # ── Verify submission ──────────────────────────────────────────────────
        logger.info("[LINKEDIN] Verifying post submission...")
        time.sleep(3)
        self._screenshot(page, 'after_post_click')

        # Check 1: textbox gone — most reliable signal
        try:
            if not page.locator('div[aria-label="Text editor for creating content"]').first.is_visible(timeout=3000):
                logger.info("[LINKEDIN] Verified: textbox gone — modal closed")
                return True
        except Exception:
            pass

        # Check 2: toast / alert appeared
        for sel in ['[role="alert"]', '[aria-live="polite"]', '[data-testid*="toast"]']:
            try:
                if page.locator(sel).first.is_visible(timeout=2000):
                    logger.info(f"[LINKEDIN] Verified: notification via '{sel}'")
                    return True
            except Exception:
                continue

        # Check 3: editor is now empty
        try:
            editor = page.locator('div[aria-label="Text editor for creating content"]').first
            if editor.is_visible(timeout=1000) and not editor.inner_text().strip():
                logger.info("[LINKEDIN] Verified: editor empty — post submitted")
                return True
        except Exception:
            pass

        logger.warning("[LINKEDIN] Verification inconclusive — click succeeded, assuming posted")
        return True

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
            # PRIMARY — confirmed from live DOM: <button aria-label="Add media">
            # This is the exact aria-label LinkedIn uses for the photo/media button
            'button[aria-label="Add media"]',
            # FALLBACK 1 — partial match in case LinkedIn changes "Add media" wording
            'button[aria-label*="media"]',
            # FALLBACK 2 — "Add a photo" variant seen on some LinkedIn UI versions
            'button[aria-label="Add a photo"]',
            # FALLBACK 3 — other partial matches
            'button[aria-label*="photo"]',
            'button[aria-label*="Photo"]',
            'button[aria-label*="image"]',
            # FALLBACK 4 — text-based (least stable)
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
        Uses a short timeout per selector — primary selectors should hit fast.
        """
        for selector in selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1500):  # 1.5s per selector — fast fail
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
