#!/usr/bin/env python3
"""
Browser Tool - Open URLs and search
Uses system default browser or Playwright for automation
"""

import webbrowser
import logging
import subprocess
import os
from typing import Dict, Any
from urllib.parse import quote

logger = logging.getLogger('BROWSER_TOOL')


class BrowserTool:
    """Browser automation and URL opening"""
    
    def __init__(self):
        logger.info("Initializing Browser Tool...")
        self.browser = None
        logger.info("[OK] Browser Tool initialized")
    
    def open_url(self, url: str, browser: str = None) -> str:
        """
        Open URL in specified browser or default browser
        
        Args:
            url: URL to open
            browser: Browser name (chrome, firefox, edge, safari) or None for default
            
        Returns:
            Success message or error
        """
        logger.info(f"[BROWSER] Opening URL: {url}" + (f" in {browser}" if browser else ""))
        
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://', 'ftp://')):
                url = 'https://' + url
            
            # Open in specified browser or default
            if browser:
                browser_lower = browser.lower().strip()
                
                # Windows browser commands
                if os.name == 'nt':
                    browser_commands = {
                        'chrome': f'start chrome "{url}"',
                        'google chrome': f'start chrome "{url}"',
                        'firefox': f'start firefox "{url}"',
                        'edge': f'start msedge "{url}"',
                        'microsoft edge': f'start msedge "{url}"',
                        'safari': f'start safari "{url}"',
                        'ie': f'start iexplore "{url}"',
                        'internet explorer': f'start iexplore "{url}"',
                    }
                    
                    cmd = browser_commands.get(browser_lower)
                    if cmd:
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        logger.info(f"[BROWSER] Opened in {browser}: {url}")
                        return f"Opened in {browser}: {url}"
                    else:
                        logger.warning(f"[BROWSER] Unknown browser: {browser}")
                        return f"Error: Unknown browser '{browser}'. Using default browser instead."
                
                # macOS browser commands
                elif os.name == 'posix' and os.uname().sysname == 'Darwin':
                    browser_commands = {
                        'chrome': f'open -a "Google Chrome" "{url}"',
                        'google chrome': f'open -a "Google Chrome" "{url}"',
                        'firefox': f'open -a Firefox "{url}"',
                        'safari': f'open -a Safari "{url}"',
                    }
                    
                    cmd = browser_commands.get(browser_lower)
                    if cmd:
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        logger.info(f"[BROWSER] Opened in {browser}: {url}")
                        return f"Opened in {browser}: {url}"
                
                # Linux browser commands
                elif os.name == 'posix':
                    browser_commands = {
                        'chrome': f'google-chrome "{url}"',
                        'google chrome': f'google-chrome "{url}"',
                        'firefox': f'firefox "{url}"',
                        'chromium': f'chromium "{url}"',
                    }
                    
                    cmd = browser_commands.get(browser_lower)
                    if cmd:
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        logger.info(f"[BROWSER] Opened in {browser}: {url}")
                        return f"Opened in {browser}: {url}"
            
            # Open in default browser
            webbrowser.open(url)
            logger.info(f"[BROWSER] Opened: {url}")
            return f"Opened URL: {url}"
        
        except Exception as e:
            logger.error(f"[BROWSER] Error opening URL: {str(e)}")
            return f"Error: {str(e)}"
    
    def search(self, query: str, engine: str = 'google') -> str:
        """
        Search the web
        
        Args:
            query: Search query
            engine: Search engine (google, bing, duckduckgo)
            
        Returns:
            Success message or error
        """
        logger.info(f"[BROWSER] Searching {engine} for: {query}")
        
        try:
            # Build search URL
            search_urls = {
                'google': f'https://www.google.com/search?q={quote(query)}',
                'bing': f'https://www.bing.com/search?q={quote(query)}',
                'duckduckgo': f'https://duckduckgo.com/?q={quote(query)}',
            }
            
            url = search_urls.get(engine, search_urls['google'])
            
            # Open in browser
            webbrowser.open(url)
            
            logger.info(f"[BROWSER] Searched {engine} for: {query}")
            return f"Searching {engine} for: {query}"
        
        except Exception as e:
            logger.error(f"[BROWSER] Error searching: {str(e)}")
            return f"Error: {str(e)}"
    
    def open_app(self, app_name: str) -> str:
        """
        Open an application
        
        Args:
            app_name: Application name
            
        Returns:
            Success message or error
        """
        logger.info(f"[BROWSER] Opening app: {app_name}")
        
        try:
            app_name_lower = app_name.lower().strip()
            
            # Windows app commands
            windows_apps = {
                'chrome': 'start chrome',
                'google chrome': 'start chrome',
                'firefox': 'start firefox',
                'edge': 'start msedge',
                'microsoft edge': 'start msedge',
                'notepad': 'start notepad',
                'calculator': 'start calc',
                'explorer': 'start explorer',
                'file explorer': 'start explorer',
                'vscode': 'start code',
                'visual studio code': 'start code',
                'cmd': 'start cmd',
                'command prompt': 'start cmd',
                'powershell': 'start powershell',
                'settings': 'start ms-settings:',
                'discord': 'start discord',
                'spotify': 'start spotify',
                'steam': 'start steam',
                'vlc': 'start vlc',
                'paint': 'start mspaint',
                'word': 'start winword',
                'excel': 'start excel',
                'powerpoint': 'start powerpnt',
                'outlook': 'start outlook',
            }
            
            # macOS app commands
            macos_apps = {
                'chrome': 'open -a "Google Chrome"',
                'google chrome': 'open -a "Google Chrome"',
                'firefox': 'open -a Firefox',
                'safari': 'open -a Safari',
                'vscode': 'open -a "Visual Studio Code"',
                'notepad': 'open -a TextEdit',
                'calculator': 'open -a Calculator',
                'finder': 'open -a Finder',
                'terminal': 'open -a Terminal',
                'discord': 'open -a Discord',
                'spotify': 'open -a Spotify',
                'vlc': 'open -a VLC',
            }
            
            # Linux app commands
            linux_apps = {
                'chrome': 'google-chrome',
                'google chrome': 'google-chrome',
                'firefox': 'firefox',
                'vscode': 'code',
                'notepad': 'gedit',
                'terminal': 'gnome-terminal',
            }
            
            # Determine OS and get command
            if os.name == 'nt':  # Windows
                cmd = windows_apps.get(app_name_lower)
            elif os.name == 'posix':
                if os.uname().sysname == 'Darwin':  # macOS
                    cmd = macos_apps.get(app_name_lower)
                else:  # Linux
                    cmd = linux_apps.get(app_name_lower)
            else:
                return f"Error: Unsupported OS"
            
            if not cmd:
                logger.warning(f"[BROWSER] Unknown app: {app_name}")
                return f"Error: Unknown app: {app_name}"
            
            # Execute command
            if os.name == 'nt':
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"[BROWSER] Opened app: {app_name}")
            return f"Opening {app_name}..."
        
        except Exception as e:
            logger.error(f"[BROWSER] Error opening app: {str(e)}")
            return f"Error: {str(e)}"
    
    def generate_image(self, prompt: str) -> str:
        """
        Generate an image using Pollinations.ai (free, no API key)
        
        Args:
            prompt: Image description
            
        Returns:
            Path to saved image or error
        """
        import httpx
        import urllib.parse
        from pathlib import Path
        from datetime import datetime
        
        logger.info(f"[BROWSER] Generating image: {prompt}")
        
        try:
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}"
            
            save_dir = Path("E:/PROJECTS/JARVIS/generated_images")
            save_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = save_dir / f"image_{timestamp}.jpg"
            
            with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r:
                with open(filename, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            
            import webbrowser
            webbrowser.open(str(filename))
            logger.info(f"[BROWSER] Image saved: {filename}")
            return f"Image saved: {filename}"
        
        except Exception as e:
            logger.error(f"[BROWSER] Image generation error: {str(e)}")
            return f"Error: {str(e)}"


def main():
    """Test browser tool"""
    tool = BrowserTool()
    
    # Test search
    print("\n=== Test Search ===")
    result = tool.search("python tutorials")
    print(result)
    
    # Test open URL
    print("\n=== Test Open URL ===")
    result = tool.open_url("github.com")
    print(result)


if __name__ == '__main__':
    main()
