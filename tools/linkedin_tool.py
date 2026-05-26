#!/usr/bin/env python3
import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path("E:/PROJECTS/JARVIS/VirtualAssistant/.env")
load_dotenv(dotenv_path=env_path, override=True)
logger = logging.getLogger('LINKEDIN_TOOL')

SESSION_FILE = Path("E:/PROJECTS/JARVIS/VirtualAssistant/linkedin_session.json")


class LinkedInTool:

    def __init__(self):
        logger.info("Initializing LinkedIn Tool...")
        logger.info("[OK] LinkedIn Tool initialized")

    def post(self, text: str, image_path: str = None) -> str:
        from playwright.sync_api import sync_playwright

        email = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')

        if not email or 'example.com' in email:
            return f"Error: LinkedIn credentials not set. Email found: '{email}'"

        logger.info(f"[LINKEDIN] Starting post...")

        with sync_playwright() as p:
            browser, page = self._open_linkedin_page(p)
            if isinstance(browser, str):
                return browser  # error string

            if "login" in page.url or "authwall" in page.url:
                context = browser.contexts[0]
                logger.info("[LINKEDIN] Not logged in, logging in...")
                result = self._login(page, email, password)
                if not result:
                    browser.close()
                    return "Error: LinkedIn login failed"
                context.storage_state(path=str(SESSION_FILE))
                logger.info("[LINKEDIN] Session saved")

            result = self._create_post(page, text, image_path)
            browser.close()
            return result

    def delete_last_post(self) -> str:
        from playwright.sync_api import sync_playwright

        email = os.getenv('LINKEDIN_EMAIL')
        if not email or 'example.com' in email:
            return f"Error: LinkedIn credentials not set. Email found: '{email}'"

        logger.info("[LINKEDIN] Starting delete last post...")

        with sync_playwright() as p:
            browser, page = self._open_linkedin_page(p)
            if isinstance(browser, str):
                return browser  # error string

            if "login" in page.url or "authwall" in page.url:
                browser.close()
                return "Error: Not logged in to LinkedIn"

            return self._delete_most_recent_post(page, browser)

    def _open_linkedin_page(self, p):
        """Launch browser, load session, navigate to feed. Returns (browser, page) or (error_str, None)."""
        browser = p.chromium.launch(headless=False)

        if SESSION_FILE.exists():
            context = browser.new_context(storage_state=str(SESSION_FILE))
            logger.info("[LINKEDIN] Loaded saved session")
        else:
            context = browser.new_context()

        page = context.new_page()

        for attempt in range(3):
            try:
                logger.info(f"[LINKEDIN] Loading feed (attempt {attempt + 1})...")
                page.goto(
                    "https://www.linkedin.com/feed/",
                    wait_until="domcontentloaded",
                    timeout=90000
                )
                break
            except Exception as nav_err:
                logger.warning(f"[LINKEDIN] Navigation attempt {attempt + 1} failed: {nav_err}")
                if attempt == 2:
                    browser.close()
                    return f"Error: Could not load LinkedIn after 3 attempts: {nav_err}", None
                time.sleep(5)

        time.sleep(5)
        return browser, page

    def _login(self, page, email: str, password: str) -> bool:
        try:
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=90000)
            time.sleep(2)
            page.fill('#username', email)
            page.fill('#password', password)
            page.click('button[type="submit"]')
            time.sleep(4)
            if "feed" in page.url or "checkpoint" in page.url:
                logger.info("[LINKEDIN] Login successful")
                return True
            return False
        except Exception as e:
            logger.error(f"[LINKEDIN] Login error: {e}")
            return False

    def _create_post(self, page, text: str, image_path: str = None) -> str:
        try:
            logger.info("[LINKEDIN] Creating post...")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)

            # Click "Start a post" - try multiple selectors
            clicked = False

            try:
                page.click('div.share-box-feed-entry__trigger', timeout=5000)
                clicked = True
                logger.info("[LINKEDIN] Clicked via share-box trigger")
            except: pass

            if not clicked:
                try:
                    page.get_by_placeholder("Start a post").click(timeout=5000)
                    clicked = True
                    logger.info("[LINKEDIN] Clicked via placeholder")
                except: pass

            if not clicked:
                try:
                    page.locator('button:has-text("Start a post")').first.click(timeout=5000)
                    clicked = True
                    logger.info("[LINKEDIN] Clicked via button text")
                except: pass

            if not clicked:
                try:
                    page.locator('div.share-box-feed-entry__top-bar').click(timeout=5000)
                    clicked = True
                    logger.info("[LINKEDIN] Clicked via top-bar")
                except: pass

            if not clicked:
                try:
                    page.get_by_text("Start a post", exact=True).first.click(timeout=5000)
                    clicked = True
                    logger.info("[LINKEDIN] Clicked via exact text")
                except: pass

            if not clicked:
                page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
                return "Could not find Start a post button. Check linkedin_debug.png"

            # Wait for post dialog to open
            time.sleep(6)
            try:
                page.wait_for_selector('div[role="dialog"]', timeout=10000)
                logger.info("[LINKEDIN] Post dialog opened")
            except:
                logger.warning("[LINKEDIN] Dialog selector not found, continuing anyway")
            time.sleep(2)

            # Debug screenshot right after dialog opens
            page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
            logger.info("[LINKEDIN] Debug screenshot saved")

            # Find text area
            textbox = None
            for selector in [
                'div[role="textbox"]',
                '.ql-editor',
                'div.editor-content',
                '[data-placeholder="What do you want to talk about?"]',
                'div.share-creation-state__text-editor div[contenteditable="true"]',
                'div[contenteditable="true"]',
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=3000):
                        textbox = el
                        logger.info(f"[LINKEDIN] Found textbox: {selector}")
                        break
                except: continue

            if not textbox:
                page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
                return "Could not find text area. Check linkedin_debug.png"

            textbox.click()
            textbox.type(text, delay=50)
            time.sleep(2)

            # Upload image if provided
            logger.info(f"[LINKEDIN] image_path param: {image_path}")
            if image_path and Path(image_path).exists():
                logger.info(f"[LINKEDIN] Uploading image: {image_path}")
                try:
                    # Use expect_file_chooser to intercept the OS file dialog
                    # before it opens — this is the correct Playwright approach
                    with page.expect_file_chooser(timeout=8000) as fc_info:
                        # Click the media/photo button inside the context manager
                        for btn_selector in [
                            'button[aria-label*="media"]',
                            'button[aria-label="Add a photo"]',
                            'button[aria-label*="photo"]',
                            'button[aria-label*="Photo"]',
                            'button[aria-label*="image"]',
                            'button:has-text("Photo")',
                            'button:has-text("Add a photo")',
                        ]:
                            try:
                                btn = page.locator(btn_selector).first
                                if btn.is_visible(timeout=2000):
                                    btn.click()
                                    logger.info(f"[LINKEDIN] Photo button clicked: {btn_selector}")
                                    break
                            except: continue

                    # Set the file on the intercepted chooser
                    file_chooser = fc_info.value
                    file_chooser.set_files(image_path)
                    logger.info("[LINKEDIN] Image set via file chooser")
                    time.sleep(6)
                    logger.info("[LINKEDIN] Image upload complete")
                except Exception as img_err:
                    logger.warning(f"[LINKEDIN] File chooser upload failed: {img_err}")
                    # Fallback: try direct set_input_files
                    try:
                        page.set_input_files('input[type="file"]', image_path)
                        logger.info("[LINKEDIN] Image uploaded via direct file input (fallback)")
                        time.sleep(6)
                    except Exception as fb_err:
                        logger.warning(f"[LINKEDIN] Fallback upload also failed: {fb_err}")
            else:
                if image_path:
                    logger.warning(f"[LINKEDIN] Image file not found: {image_path}")

            # Preview screenshot
            screenshot_path = "E:/PROJECTS/JARVIS/generated_images/linkedin_preview.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"[LINKEDIN] Preview saved: {screenshot_path}")

            # Click Post button — try all known selectors
            post_selectors = [
                'button.share-actions__primary-action',
                'button[aria-label="Post"]',
                'button[aria-label*="Post"]',
                'div[role="dialog"] button:has-text("Post")',
                'button:has-text("Post")',
                '[data-control-name="share.post"]',
                'button.artdeco-button--primary:has-text("Post")',
            ]
            for selector in post_selectors:
                try:
                    btn = page.locator(selector).last
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        logger.info(f"[LINKEDIN] Posted via: {selector}")
                        time.sleep(3)
                        return f"Posted to LinkedIn! Preview: {screenshot_path}"
                except: continue

            # Last resort: find any primary action button in the dialog
            try:
                btns = page.locator('div[role="dialog"] button.artdeco-button--primary')
                count = btns.count()
                logger.info(f"[LINKEDIN] Found {count} primary buttons in dialog")
                if count > 0:
                    btns.last.click()
                    logger.info("[LINKEDIN] Posted via last primary button")
                    time.sleep(3)
                    return f"Posted to LinkedIn! Preview: {screenshot_path}"
            except: pass

            return f"Typed post but could not click Post button. Preview: {screenshot_path}"

        except Exception as e:
            logger.error(f"[LINKEDIN] Post error: {e}")
            try:
                page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_error.png")
            except: pass
            return f"Error posting: {str(e)}"

    def _delete_most_recent_post(self, page, browser) -> str:
        """Navigate to own profile, find the most recent post, delete it."""
        try:
            logger.info("[LINKEDIN] Navigating to profile to find latest post...")

            # Go to own profile via /in/me redirect
            page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=90000)
            time.sleep(4)

            # Scroll down a bit so posts section loads
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(3)

            # Screenshot to see profile state
            page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
            logger.info("[LINKEDIN] Profile screenshot saved")

            # Find the three-dot menu on the first/most recent post
            # LinkedIn uses aria-label like "Open control menu for this post"
            three_dot_selectors = [
                'button[aria-label*="Open control menu"]',
                'button[aria-label*="control menu"]',
                'button[aria-label*="More options"]',
                'button[aria-label*="more options"]',
                '.feed-shared-control-menu__trigger',
                'button.artdeco-dropdown__trigger:has(li-icon[type="overflow-web-ios-medium"])',
            ]

            three_dot = None
            for selector in three_dot_selectors:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=4000):
                        three_dot = el
                        logger.info(f"[LINKEDIN] Found three-dot menu: {selector}")
                        break
                except: continue

            if not three_dot:
                page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
                browser.close()
                return "Could not find post menu button. Check linkedin_debug.png"

            three_dot.click()
            time.sleep(3)  # wait for dropdown to fully render

            # Screenshot the open dropdown
            page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
            logger.info("[LINKEDIN] Dropdown screenshot saved")

            # Click Delete in the dropdown — LinkedIn uses <a role="menuitem"> not <button>
            delete_selectors = [
                'a[role="menuitem"]:has-text("Delete post")',
                'div[role="menuitem"]:has-text("Delete post")',
                '[role="menuitem"]:has-text("Delete post")',
                '[role="menuitem"]:has-text("Delete")',
            ]

            deleted = False
            for selector in delete_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        logger.info(f"[LINKEDIN] Clicked Delete via: {selector}")
                        deleted = True
                        break
                except: continue

            if not deleted:
                page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_debug.png")
                browser.close()
                return "Could not find Delete option in menu. Check linkedin_debug.png"

            time.sleep(2)

            # Confirm deletion in the confirmation dialog
            confirm_selectors = [
                'div[role="dialog"] button:has-text("Delete")',
                'button.artdeco-button--primary:has-text("Delete")',
                'button[aria-label*="Delete"]',
                'button:has-text("Delete")',
            ]

            confirmed = False
            for selector in confirm_selectors:
                try:
                    btn = page.locator(selector).last
                    if btn.is_visible(timeout=4000):
                        btn.click()
                        logger.info(f"[LINKEDIN] Confirmed delete via: {selector}")
                        confirmed = True
                        break
                except: continue

            time.sleep(3)
            page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_preview.png")
            browser.close()

            if confirmed:
                return "Deleted most recent LinkedIn post successfully."
            else:
                return "Delete clicked but confirmation dialog not found — post may still be deleted. Check linkedin_preview.png"

        except Exception as e:
            logger.error(f"[LINKEDIN] Delete error: {e}")
            try:
                page.screenshot(path="E:/PROJECTS/JARVIS/generated_images/linkedin_error.png")
            except: pass
            browser.close()
            return f"Error deleting post: {str(e)}"
