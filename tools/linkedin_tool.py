#!/usr/bin/env python3
"""
LinkedIn Tool - Post, delete, and manage LinkedIn content via Playwright.
Deterministic State Machine implementation.
"""

import os
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

env_path = Path("E:/PROJECTS/JARVIS/VirtualAssistant/.env")
load_dotenv(dotenv_path=env_path, override=True)
logger = logging.getLogger('LINKEDIN_TOOL')

SESSION_FILE    = Path("E:/PROJECTS/JARVIS/VirtualAssistant/linkedin_session.json")
SCREENSHOT_DIR  = Path("E:/PROJECTS/JARVIS/generated_images")
SELECTOR_RETRIES = 3
SELECTOR_WAIT    = 3000


class LinkedInTool:

    # State constants
    STATE_COMPOSER = 'COMPOSER'
    STATE_IMAGE_PREVIEW = 'IMAGE_PREVIEW'
    STATE_TRANSITIONING = 'TRANSITIONING_TO_COMPOSER'
    STATE_POST_READY = 'POST_READY'
    STATE_UNKNOWN = 'STATE_UNKNOWN'

    def __init__(self):
        logger.info("Initializing LinkedIn Tool...")
        self.logs = []
        self.screenshots = []
        logger.info("[OK] LinkedIn Tool initialized")

    def _log(self, msg: str):
        logger.info(msg)
        self.logs.append(msg)

    def _add_screenshot(self, path: str):
        self.screenshots.append(path)

    def _make_result(self, status: str, state: str, message: str) -> Dict[str, Any]:
        return {
            "status": status,
            "logs": list(self.logs),
            "screenshots": list(self.screenshots),
            "state": state,
            "result": {"message": message}
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def post(self, text: str, image_path: str = None) -> Dict[str, Any]:
        from playwright.sync_api import sync_playwright

        self.logs = []
        self.screenshots = []

        email    = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')

        if not email or 'example.com' in email:
            self._log("[LINKEDIN] Error: LinkedIn credentials not set in environment.")
            return self._make_result("failed", self.STATE_UNKNOWN, "Error: LinkedIn credentials not set.")

        self._log("[LINKEDIN] Starting post workflow...")

        with sync_playwright() as p:
            browser, page = self._open_linkedin_page(p)
            if isinstance(browser, str):
                self._log(f"[LINKEDIN] Navigation error: {browser}")
                return self._make_result("failed", self.STATE_UNKNOWN, browser)

            # Detect expired / missing session
            if self._is_session_expired(page):
                self._log("[LINKEDIN] Session expired or not logged in — re-logging in")
                context = browser.contexts[0]
                login_success, failure_reason = self._login(page, email, password)
                if not login_success:
                    self._screenshot(page, 'login_failed')
                    browser.close()
                    return self._make_result("failed", self.STATE_UNKNOWN, failure_reason)
                context.storage_state(path=str(SESSION_FILE))
                self._log("[LINKEDIN] Session saved after fresh login")

            result_str = self._create_post(page, text, image_path)
            browser.close()
            
            status = "success" if not result_str.startswith("Error:") else "failed"
            state = self.STATE_POST_READY if status == "success" else self.STATE_UNKNOWN
            return self._make_result(status, state, result_str)

    def delete_last_post(self) -> Dict[str, Any]:
        from playwright.sync_api import sync_playwright

        self.logs = []
        self.screenshots = []

        email = os.getenv('LINKEDIN_EMAIL')
        if not email or 'example.com' in email:
            self._log("[LINKEDIN] Error: LinkedIn credentials not set.")
            return self._make_result("failed", self.STATE_UNKNOWN, "Error: LinkedIn credentials not set.")

        self._log("[LINKEDIN] Starting delete-last-post workflow...")

        with sync_playwright() as p:
            browser, page = self._open_linkedin_page(p)
            if isinstance(browser, str):
                self._log(f"[LINKEDIN] Navigation error: {browser}")
                return self._make_result("failed", self.STATE_UNKNOWN, browser)

            if self._is_session_expired(page):
                curr_url = page.url
                curr_title = page.title()
                self._log(f"[LINKEDIN] Session expired — URL: {curr_url} | Title: '{curr_title}'")
                self._screenshot(page, 'session_expired')
                browser.close()
                return self._make_result("failed", self.STATE_UNKNOWN, f"Error: LinkedIn session expired. Current URL: {curr_url} | Title: '{curr_title}'")

            result_str = self._delete_most_recent_post(page, browser)
            status = "success" if not result_str.startswith("Error:") else "failed"
            return self._make_result(status, self.STATE_UNKNOWN, result_str)

    # ── Session helpers ────────────────────────────────────────────────────────

    def _is_session_expired(self, page) -> bool:
        url = page.url.lower()
        title = page.title()
        self._log(f"[LINKEDIN] Checking session status — Current URL: {page.url} | Title: '{title}'")
        expired_signals = ('login', 'authwall', 'session-expired', 'uas/authenticate', 'sign-in')
        if any(s in url for s in expired_signals):
            self._log(f"[LINKEDIN] Session expired — URL: {page.url} | Title: '{title}'")
            return True

        try:
            if page.locator('#username').is_visible(timeout=1500):
                self._log(f"[LINKEDIN] Session expired — login form visible on page. Current URL: {page.url} | Title: '{title}'")
                return True
        except Exception:
            pass

        return False

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _open_linkedin_page(self, p):
        browser = p.chromium.launch(headless=False)

        if SESSION_FILE.exists():
            context = browser.new_context(storage_state=str(SESSION_FILE))
            self._log("[LINKEDIN] Loaded saved session from disk")
        else:
            context = browser.new_context()
            self._log("[LINKEDIN] No saved session — starting fresh context")

        page = context.new_page()

        for attempt in range(1, 4):
            try:
                self._log(f"[LINKEDIN] Navigating to feed (attempt {attempt}/3)...")
                page.goto(
                    "https://www.linkedin.com/feed/",
                    wait_until="domcontentloaded",
                    timeout=90000,
                )
                self._log(f"[LINKEDIN] Feed loaded — Current URL: {page.url} | Title: '{page.title()}'")
                break
            except Exception as nav_err:
                self._log(f"[LINKEDIN] Navigation attempt {attempt} failed: {nav_err}")
                if attempt == 3:
                    browser.close()
                    return f"Error: Could not load LinkedIn after 3 attempts: {nav_err}", None
                time.sleep(5)

        time.sleep(5)
        return browser, page

    def _login(self, page, email: str, password: str) -> tuple:
        """
        Navigates to login page, fills credentials, and submits.
        Returns tuple (success: bool, failure_reason: str).
        Performs full diagnostic checks (URL, title, failed selectors, failure types).
        """
        failed_selector = None
        try:
            self._log("[LINKEDIN] Navigating to login page...")
            page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=90000,
            )
            time.sleep(2)

            curr_url = page.url
            curr_title = page.title()
            self._log(f"[LINKEDIN] Login page loaded — Current URL: {curr_url} | Title: '{curr_title}'")

            # Locate username input
            username_selectors = ['#username', 'input[name="session_key"]', '#session_key']
            user_el = self._find_visible(page, username_selectors, label="username input")
            if not user_el:
                failed_selector = '#username'
                self._log(f"[LINKEDIN] Failed selector: {failed_selector}")
                self._log(f"[LINKEDIN] Login failed due to selector failure — Current URL: {curr_url} | Title: '{curr_title}'")
                self._screenshot(page, 'login_failed')
                return False, f"Error: LinkedIn login failed due to selector failure ('{failed_selector}'). Current URL: {curr_url} | Title: '{curr_title}'"

            user_el.fill(email)

            # Locate password input
            password_selectors = ['#password', 'input[name="session_password"]', '#session_password']
            pass_el = self._find_visible(page, password_selectors, label="password input")
            if not pass_el:
                failed_selector = '#password'
                self._log(f"[LINKEDIN] Failed selector: {failed_selector}")
                self._log(f"[LINKEDIN] Login failed due to selector failure — Current URL: {curr_url} | Title: '{curr_title}'")
                self._screenshot(page, 'login_failed')
                return False, f"Error: LinkedIn login failed due to selector failure ('{failed_selector}'). Current URL: {curr_url} | Title: '{curr_title}'"

            pass_el.fill(password)

            # Locate submit button
            submit_selectors = ['button[type="submit"]', 'button:has-text("Sign in")', 'button:has-text("Log in")']
            sub_btn = self._find_visible(page, submit_selectors, label="submit button")
            if not sub_btn:
                failed_selector = 'button[type="submit"]'
                self._log(f"[LINKEDIN] Failed selector: {failed_selector}")
                self._log(f"[LINKEDIN] Login failed due to selector failure — Current URL: {curr_url} | Title: '{curr_title}'")
                self._screenshot(page, 'login_failed')
                return False, f"Error: LinkedIn login failed due to selector failure ('{failed_selector}'). Current URL: {curr_url} | Title: '{curr_title}'"

            sub_btn.click()
            time.sleep(5)

            end_url = page.url.lower()
            end_title = page.title()
            self._log(f"[LINKEDIN] Post-login check — Current URL: {page.url} | Title: '{end_title}'")

            # Check 1: Success (feed page loaded)
            if "feed" in end_url:
                self._log(f"[LINKEDIN] Login successful — Current URL: {page.url} | Title: '{end_title}'")
                return True, "Login successful"

            # Check 2: LinkedIn Verification Page (checkpoint / pin / captcha / challenge)
            if any(k in end_url for k in ('checkpoint', 'challenge', 'captcha', 'pin', 'security-check', 'verification')) or any(k in end_title.lower() for k in ('verification', 'checkpoint', 'security', 'pin')):
                reason = f"Error: LinkedIn requires security verification page. Current URL: {page.url} | Title: '{end_title}'"
                self._log(f"[LINKEDIN] {reason}")
                self._screenshot(page, 'login_failed')
                return False, reason

            # Check 3: Invalid Credentials
            try:
                err_msg = page.locator('#error-for-username, #error-for-password, .alert--error, [role="alert"]').first
                if err_msg.is_visible(timeout=2000):
                    err_text = err_msg.inner_text().strip().replace('\n', ' ')
                    reason = f"Error: LinkedIn credentials invalid ({err_text}). Current URL: {page.url} | Title: '{end_title}'"
                    self._log(f"[LINKEDIN] {reason}")
                    self._screenshot(page, 'login_failed')
                    return False, reason
            except Exception:
                pass

            # Check 4: Session Expired / Authwall redirect
            if any(k in end_url for k in ('login', 'authwall', 'session-expired', 'uas/authenticate', 'sign-in')):
                reason = f"Error: LinkedIn session expired. Current URL: {page.url} | Title: '{end_title}'"
                self._log(f"[LINKEDIN] {reason}")
                self._screenshot(page, 'login_failed')
                return False, reason

            # Generic failure reporting
            reason = f"Error: LinkedIn login failed. Current URL: {page.url} | Title: '{end_title}'"
            self._log(f"[LINKEDIN] {reason}")
            self._screenshot(page, 'login_failed')
            return False, reason

        except Exception as e:
            curr_url = page.url if page else 'unknown'
            curr_title = page.title() if page else 'unknown'
            reason = f"Error: LinkedIn login failed ({str(e)}). Current URL: {curr_url} | Title: '{curr_title}'"
            self._log(f"[LINKEDIN] {reason}")
            if page:
                self._screenshot(page, 'login_failed')
            return False, reason

    # ── Core: create post ──────────────────────────────────────────────────────

    def _get_active_dialog(self, page):
        """Find the active modal dialog on the page. Returns Playwright locator."""
        for selector in ['div.share-creation-state', 'div[role="dialog"]', '.share-box-feed-entry__dialog']:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=500):
                    return el
            except Exception:
                continue
        return page

    def detect_linkedin_post_state(self, page) -> str:
        """
        Inspect visible buttons inside the dialog modal to determine state.
        """
        dialog = self._get_active_dialog(page)
        try:
            # 1. Check if we are in IMAGE_PREVIEW (Image Editor):
            # Look for Back and Next/Done buttons inside the dialog
            back_visible = dialog.locator('button[aria-label="Back"], button:has-text("Back")').first.is_visible(timeout=500)
            next_visible = dialog.locator('button[aria-label="Next"], button:has-text("Next")').first.is_visible(timeout=500)
            done_visible = dialog.locator('button[aria-label="Done"], button:has-text("Done")').first.is_visible(timeout=500)
            
            if (next_visible or done_visible) and back_visible:
                return self.STATE_IMAGE_PREVIEW
                
            # 2. Check if we are TRANSITIONING_TO_COMPOSER (AltText/Intermediate Done screen)
            if (next_visible or done_visible) and not back_visible:
                return self.STATE_TRANSITIONING
                
            # 3. Check if textbox is visible
            textbox_visible = dialog.locator('div[aria-label="Text editor for creating content"], div[role="textbox"]').first.is_visible(timeout=500)
            if textbox_visible:
                # If image is attached, preview image or Remove media button exists
                img_preview = dialog.locator('img, .share-media-preview__image-renderer, .share-native-video-preview, button[aria-label="Remove media"]').first.is_visible(timeout=500)
                if img_preview:
                    return self.STATE_POST_READY
                else:
                    return self.STATE_COMPOSER
                    
        except Exception as e:
            self._log(f"[STATE] Detection error: {e}")
            
        return self.STATE_UNKNOWN

    def _create_post(self, page, text: str, image_path: str = None) -> str:
        try:
            self._log("[LINKEDIN] Starting _create_post (state-based)...")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)

            # ── Step 1: click "Start a post" ──────────────────────────────────
            self._log("[LINKEDIN] Step 1: clicking 'Start a post'...")
            start_post_selectors = [
                'div[aria-label="Start a post"]',
                '[placeholder="Start a post"]',
                'button[aria-label="Start a post"]',
                'div.share-box-feed-entry__trigger',
            ]
            clicked = self._click_with_retry(page, start_post_selectors, label="Start a post")

            if not clicked:
                try:
                    page.get_by_text("Start a post", exact=True).first.click(timeout=5000)
                    clicked = True
                    self._log("[LINKEDIN] Clicked 'Start a post' via get_by_text fallback")
                except Exception:
                    pass

            if not clicked:
                self._screenshot(page, 'start_post_not_found')
                return "Error: Could not find 'Start a post' button."

            # ── Step 2: wait for composer to open ─────────────────────────────
            self._log("[LINKEDIN] Step 2: waiting for composer...")
            textbox_ready = False
            for _ in range(10):
                dialog = self._get_active_dialog(page)
                try:
                    el = dialog.locator('div[aria-label="Text editor for creating content"]').first
                    if el.is_visible(timeout=2000):
                        textbox_ready = True
                        self._log("[LINKEDIN] Composer textbox is visible")
                        break
                except Exception:
                    pass
                time.sleep(2)

            if not textbox_ready:
                self._log("[LINKEDIN] Textbox not visible after 20s — checking state anyway")

            self._screenshot(page, 'dialog_opened')

            # ── Step 3: find and fill textbox ─────────────────────────────────
            self._log("[LINKEDIN] Step 3: locating text area...")
            textbox_selectors = [
                'div[aria-label="Text editor for creating content"]',
                '[data-placeholder="What do you want to talk about?"]',
                'div[role="textbox"]',
                '.ql-editor',
                'div[contenteditable="true"]',
            ]
            
            dialog = self._get_active_dialog(page)
            for selector in textbox_selectors[:3]:
                try:
                    dialog.locator(selector).first.wait_for(state="visible", timeout=15000)
                    self._log(f"[LINKEDIN] Textbox selector '{selector}' is visible")
                    break
                except Exception:
                    continue

            textbox = self._find_visible(dialog, textbox_selectors, label="textbox")

            if not textbox:
                self._screenshot(page, 'textbox_not_found')
                return "Error: Could not find post text area."

            textbox.click()
            textbox.type(text, delay=50)
            self._log(f"[LINKEDIN] Typed post text ({len(text)} chars)")
            time.sleep(2)

            # ── Step 4: upload image + state transition ────────────────────────
            if image_path:
                self._upload_image(page, image_path)
                self._screenshot(page, 'after_upload')

                self._log("[LINKEDIN] Step 4b: detecting state after image upload...")
                time.sleep(3)
                state = self.detect_linkedin_post_state(page)

                if state == self.STATE_IMAGE_PREVIEW:
                    self._log("[STATE] TransitioningToComposer — clicking Next/Done inside image editor...")
                    self._screenshot(page, 'before_next_click')

                    next_clicked = False
                    try:
                        dialog = self._get_active_dialog(page)
                        done_btn = dialog.locator('button:has-text("Done"), button[aria-label="Done"]').first
                        next_btn = dialog.locator('button:has-text("Next"), button[aria-label="Next"]').first
                        
                        if done_btn.is_visible(timeout=2000):
                            done_btn.click(force=True)
                            next_clicked = True
                            self._log("[LINKEDIN] Clicked image editor 'Done' button")
                        elif next_btn.is_visible(timeout=2000):
                            next_btn.click(force=True)
                            next_clicked = True
                            self._log("[LINKEDIN] Clicked image editor 'Next' button")
                    except Exception as e:
                        self._log(f"[LINKEDIN] Next click error: {e}")

                    if next_clicked:
                        self._log("[LINKEDIN] Waiting for next state...")
                        time.sleep(4)
                        self._screenshot(page, 'after_next_click')

                        for attempt in range(8):
                            state = self.detect_linkedin_post_state(page)
                            if state in (self.STATE_COMPOSER, self.STATE_POST_READY):
                                self._log(f"[STATE] Transition complete: {state}")
                                break
                            elif state == self.STATE_TRANSITIONING:
                                self._log("[STATE] Transitioning — clicking Next/Done on intermediate screen...")
                                try:
                                    dialog = self._get_active_dialog(page)
                                    next_btn = dialog.locator('button:has-text("Next"), button[aria-label="Next"], button:has-text("Done"), button[aria-label="Done"]').first
                                    if next_btn.is_visible(timeout=2000):
                                        next_btn.click(force=True)
                                except Exception as e:
                                    self._log(f"[STATE] AltText Next click error: {e}")
                                time.sleep(3)
                                continue
                            self._log(f"[STATE] Current state: {state} (attempt {attempt+1}/8)...")
                            time.sleep(2)

            # ── Step 5: verify we are in POST_READY / COMPOSER state before posting ───────────────
            self._log("[LINKEDIN] Step 5: verifying composer state before Post...")
            final_state = self.detect_linkedin_post_state(page)
            self._log(f"[LINKEDIN] Verified State: {final_state}")

            preview_path = str(SCREENSHOT_DIR / "linkedin_preview.png")
            page.screenshot(path=preview_path)
            self._add_screenshot(preview_path)
            self._log(f"[LINKEDIN] Preview screenshot saved: {preview_path}")

            # ── Step 6: click Post button ──────────────────────────────────────
            self._log("[LINKEDIN] Step 6: clicking Post button...")
            posted = self._click_post_button(page)

            if not posted:
                self._screenshot(page, 'post_button_not_found')
                return f"Error: Could not click Post button."

            self._log("[LINKEDIN] Post submitted successfully")
            return f"Posted to LinkedIn! Preview: {preview_path}"

        except Exception as e:
            self._log(f"[LINKEDIN] _create_post error: {e}")
            self._screenshot(page, 'create_post_error')
            return f"Error posting: {str(e)}"

    # ── Core: delete post ──────────────────────────────────────────────────────

    def _delete_most_recent_post(self, page, browser) -> str:
        try:
            self._log("[LINKEDIN] Navigating to recent activity posts page...")
            try:
                page.goto(
                    "https://www.linkedin.com/in/me/recent-activity/shares/",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                time.sleep(4)
                if "recent-activity" not in page.url:
                    raise Exception("Redirected away from recent-activity page")
            except Exception as e:
                self._log(f"[LINKEDIN] Direct activity navigation failed ({e}) — falling back to profile page...")
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
            self._log("[LINKEDIN] Step 1: finding three-dot menu...")
            three_dot_selectors = [
                'button[aria-label*="Open control menu"]',
                'button[aria-label*="control menu"]',
                'button[aria-label^="Control menu for"]',
                'button[aria-label*="More options"]',
                'button[aria-label*="more options"]',
                'button[aria-label*="options"]',
                'button[aria-label*="Options"]',
                'button[aria-haspopup="menu"]',
                'button[aria-haspopup="true"]',
                'button[id^="control-menu-trigger-"]',
                '.feed-shared-control-menu__trigger',
                'button.feed-shared-control-menu__trigger',
            ]
            clicked = self._click_with_retry(page, three_dot_selectors, label="three-dot menu")

            if not clicked:
                self._screenshot(page, 'three_dot_not_found')
                browser.close()
                return "Error: Could not find post menu button."

            time.sleep(3)
            self._screenshot(page, 'dropdown_open')

            # ── Step 2: click Delete ──────────────────────────────────────────
            self._log("[LINKEDIN] Step 2: clicking Delete in dropdown...")
            delete_selectors = [
                'text="Delete post"',
                'text=Delete post',
                '.artdeco-dropdown__content :has-text("Delete post")',
                'span:has-text("Delete post")',
                'div:has-text("Delete post")',
                'button:has-text("Delete post")',
                '[role="menuitem"]:has-text("Delete post")',
                'text="Delete"',
                'text=Delete',
                '.artdeco-dropdown__content :has-text("Delete")',
                'span:has-text("Delete")',
                'button:has-text("Delete")',
            ]
            deleted = self._click_with_retry(page, delete_selectors, label="Delete menu item")

            if not deleted:
                self._screenshot(page, 'delete_option_not_found')
                browser.close()
                return "Error: Could not find Delete option in menu."

            time.sleep(2)

            # ── Step 3: confirm deletion ──────────────────────────────────────
            self._log("[LINKEDIN] Step 3: confirming deletion...")
            confirm_selectors = [
                'div[role="dialog"] button:has-text("Delete")',
                'button.artdeco-button--primary:has-text("Delete")',
                '.artdeco-button:has-text("Delete")',
                'button[aria-label*="Delete"]',
                'button:has-text("Delete")',
                'text="Delete"',
                'text=Delete',
            ]
            confirmed = self._click_with_retry(
                page, confirm_selectors, label="Delete confirm button", wait_ms=4000
            )

            time.sleep(3)
            self._screenshot(page, 'after_delete')
            browser.close()

            if confirmed:
                self._log("[LINKEDIN] Post deleted successfully")
                return "Deleted most recent LinkedIn post successfully."
            return "Delete clicked but confirmation not found."

        except Exception as e:
            self._log(f"[LINKEDIN] _delete_most_recent_post error: {e}")
            self._screenshot(page, 'delete_error')
            try:
                browser.close()
            except Exception:
                pass
            return f"Error deleting post: {str(e)}"

    # ── Post button: Playwright-native click ──────────────────────────────────

    def _click_post_button(self, page) -> bool:
        self._screenshot(page, 'before_post_click')
        dialog = self._get_active_dialog(page)

        for attempt in range(1, 4):
            self._log(f"[LINKEDIN] Post click attempt {attempt}/3...")
            try:
                btn = dialog.get_by_role('button', name='Post', exact=True).first
                if btn.is_visible(timeout=3000):
                    btn.scroll_into_view_if_needed(timeout=3000)
                    btn.click(force=True, timeout=5000)
                    self._log(f"[LINKEDIN] Post button clicked (attempt {attempt}/3)")
                    break
            except Exception as e:
                self._log(f"[LINKEDIN] Post click attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                time.sleep(1)
        else:
            self._log("[LINKEDIN] All Post click attempts failed")
            self._screenshot(page, 'post_click_failed')
            return False

        # ── Verify submission ──────────────────────────────────────────────────
        self._log("[LINKEDIN] Verifying post submission...")
        time.sleep(3)
        self._screenshot(page, 'after_post_click')

        # Check: textbox gone
        dialog = self._get_active_dialog(page)
        try:
            if not dialog.locator('div[aria-label="Text editor for creating content"]').first.is_visible(timeout=3000):
                self._log("[LINKEDIN] Verified: textbox is gone — modal dialog closed successfully")
                return True
        except Exception:
            pass

        return True

    # ── Image upload ───────────────────────────────────────────────────────────

    def _upload_image(self, page, image_path: str) -> None:
        self._log(f"[LINKEDIN] Uploading image: {image_path}")

        if not Path(image_path).exists():
            self._log(f"[LINKEDIN] Image file not found — skipping: {image_path}")
            return

        photo_selectors = [
            'button[aria-label="Add media"]',
            'button[aria-label*="media"]',
            'button[aria-label="Add a photo"]',
            'button[aria-label*="photo"]',
            'button[aria-label*="Photo"]',
            'button[aria-label*="image"]',
            'button:has-text("Photo")',
        ]

        dialog = self._get_active_dialog(page)
        try:
            with page.expect_file_chooser(timeout=8000) as fc_info:
                clicked = self._click_with_retry(
                    dialog, photo_selectors, label="photo button"
                )
                if not clicked:
                    self._log("[LINKEDIN] Photo button not found — skipping image upload")
                    return

            fc_info.value.set_files(image_path)
            self._log("[LINKEDIN] Image set via file chooser")
            time.sleep(6)
            self._log("[LINKEDIN] Image upload complete")

        except Exception as img_err:
            self._log(f"[LINKEDIN] File chooser failed: {img_err} — trying direct input")
            try:
                page.set_input_files('input[type="file"]', image_path)
                self._log("[LINKEDIN] Image uploaded via direct file input (fallback)")
                time.sleep(6)
            except Exception as fb_err:
                self._log(f"[LINKEDIN] Direct file input also failed: {fb_err}")

    # ── Shared utilities ───────────────────────────────────────────────────────

    def _click_with_retry(
        self,
        parent,
        selectors: list,
        label: str = "element",
        retries: int = SELECTOR_RETRIES,
        wait_ms: int = SELECTOR_WAIT,
    ) -> bool:
        for selector in selectors:
            for attempt in range(1, retries + 1):
                try:
                    el = parent.locator(selector).first
                    if el.is_visible(timeout=wait_ms):
                        el.click()
                        self._log(
                            f"[LINKEDIN] Clicked {label} "
                            f"via '{selector}' (attempt {attempt}/{retries})"
                        )
                        return True
                except Exception as e:
                    pass
                if attempt < retries:
                    time.sleep(0.5)
        self._log(f"[LINKEDIN] Could not click {label} — all selectors tried")
        return False

    def _find_visible(self, parent, selectors: list, label: str = "element"):
        for selector in selectors:
            try:
                el = parent.locator(selector).first
                if el.is_visible(timeout=1500):
                    self._log(f"[LINKEDIN] Found visible {label}: '{selector}'")
                    return el
            except Exception:
                continue
        return None

    def _screenshot(self, page, tag: str) -> str:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(SCREENSHOT_DIR / f"linkedin_{tag}_{ts}.png")
        try:
            page.screenshot(path=path)
            self._log(f"[LINKEDIN] Screenshot saved: {path}")
            self._add_screenshot(path)
        except Exception as e:
            self._log(f"[LINKEDIN] Could not save screenshot: {e}")
        return path
