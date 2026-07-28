import time
import platform
import psutil
import feedparser
import requests
import subprocess
import os
import webbrowser
from fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("JarvisSystemTools")

@mcp.tool()
def get_system_time() -> str:
    """Returns the current system time and date. Use this when the user asks for the time."""
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")

@mcp.tool()
def get_system_info() -> str:
    """Returns basic system diagnostics like OS version, CPU usage, and Memory usage. Use this when the user asks about system performance or specs."""
    return f"""
    OS: {platform.system()} {platform.release()}
    CPU Usage: {psutil.cpu_percent()}%
    Memory Usage: {psutil.virtual_memory().percent}%
    """

@mcp.tool()
def get_latest_news(category: str = "general") -> str:
    """
    Fetches the latest news headlines. 
    It automatically opens the top 3 news stories in your browser and returns headlines for JARVIS to speak.
    Categories: general, technology, business, science, health.
    """
    feeds = {
        "general": "http://feeds.bbci.co.uk/news/rss.xml",
        "technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "business": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "science": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "health": "http://feeds.bbci.co.uk/news/health/rss.xml"
    }
    
    url = feeds.get(category.lower(), feeds["general"])
    try:
        feed = feedparser.parse(url)
        news_items = []
        
        # Open top 3 articles
        for entry in feed.entries[:3]:
            if platform.system() == "Darwin":
                subprocess.run(["open", "-a", "Google Chrome", entry.link])
            else:
                webbrowser.open(entry.link)
            news_items.append(f"Headline: {entry.title}")
        
        if not news_items:
            return "I couldn't find any news articles at the moment, sir."
            
        return "Sir, I've opened the top three stories in your browser. The headlines are:\n" + "\n".join(news_items)
    except Exception as e:
        return f"Error fetching news: {str(e)}"

@mcp.tool()
def summarize_website(url: str) -> str:
    """
    Fetches the content of a website and extracts the main text for summarization.
    Use this when the user provides a specific link they want to discuss or summarize.
    """
    try:
        from bs4 import BeautifulSoup
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Return first 2000 characters to stay within LLM context
        return text[:2000]
    except Exception as e:
        return f"Error accessing website: {str(e)}"

@mcp.tool()
def open_application(app_name: str) -> str:
    """
    Opens a desktop application by name. 
    Examples: 'Chrome', 'Spotify', 'Notepad', 'Explorer', 'Visual Studio Code'.
    """
    # Mappings for common apps depending on OS
    if platform.system() == "Darwin":
        app_map = {
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "browser": "Safari",
            "safari": "Safari",
            "music": "Music",
            "spotify": "Spotify",
            "vs code": "Visual Studio Code",
            "code": "Visual Studio Code",
            "notes": "Notes",
            "terminal": "Terminal",
            "finder": "Finder"
        }
        target_app = app_map.get(app_name.lower(), app_name)
        try:
            result = subprocess.run(["open", "-a", target_app], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Successfully opened {target_app}, sir."
            return f"Failed to open {target_app}. Please check application name."
        except Exception as e:
            return f"Error opening app: {str(e)}"
            
    elif platform.system() == "Windows":
        app_map = {
            "chrome": "chrome",
            "google chrome": "chrome",
            "browser": "msedge",
            "safari": "msedge",
            "edge": "msedge",
            "vs code": "code",
            "vscode": "code",
            "code": "code",
            "notes": "notepad",
            "notepad": "notepad",
            "terminal": "cmd",
            "cmd": "cmd",
            "powershell": "powershell",
            "finder": "explorer",
            "explorer": "explorer"
        }
        target_app = app_map.get(app_name.lower(), app_name)
        try:
            # Use 'start' in shell to run target executable
            subprocess.run(f"start {target_app}", shell=True, check=True)
            return f"Successfully launched {target_app}, sir."
        except Exception as e:
            return f"Error trying to launch {app_name}: {str(e)}"
    else:
        return f"Opening applications is not supported on {platform.system()}."

@mcp.tool()
def open_url(url: str, browser: str = "default") -> str:
    """
    Opens a URL in the browser. 
    browser: 'default', 'chrome', 'safari'
    """
    if not url.startswith("http"):
        url = "https://" + url
        
    try:
        if platform.system() == "Darwin":
            if browser.lower() == "chrome":
                subprocess.run(["open", "-a", "Google Chrome", url])
                return f"Opening {url} in Chrome, sir."
            elif browser.lower() == "safari":
                subprocess.run(["open", "-a", "Safari", url])
                return f"Opening {url} in Safari, sir."
            else:
                subprocess.run(["open", url])
                return f"Opening {url} in default browser, sir."
        else:
            if browser.lower() == "chrome":
                try:
                    webbrowser.get('chrome').open(url)
                    return f"Opening {url} in Chrome, sir."
                except webbrowser.Error:
                    webbrowser.open(url)
                    return f"Opening {url} in default browser (Chrome not found), sir."
            else:
                webbrowser.open(url)
                return f"Opening {url} in default browser, sir."
    except Exception as e:
        return f"Error opening URL: {str(e)}"

@mcp.tool()
def setup_workspace(mode: str, dynamic_urls: list[str] = None) -> str:
    """
    Automates the setup of the user's workspace based on the specified mode.
    
    Modes available:
    - 'coding': Terminal/Command Prompt, Notes/Notepad, Chrome (GitHub, StackOverflow, YouTube for music)
    - 'content_creation': Photos, Chrome (YouTube Studio, X/Twitter)
    - 'research': Notepad, Chrome (Google)
    - 'relax': Music/Spotify, Chrome (YouTube)
    - 'design': Chrome (Figma, Dribbble, Pinterest)
    - 'finance': Chrome (TradingView, Yahoo Finance)
    - 'gaming': Chrome (Twitch, YouTube Gaming, Discord Web)
    - 'web_dev': Terminal/Command Prompt, Chrome (GitHub, StackOverflow, localhost:3000)
    - 'custom': Use this mode for specific topics/research. You MUST provide 'dynamic_urls'.
    """
    mode = mode.lower()
    if dynamic_urls is None:
        dynamic_urls = []
        
    workflows = {
        'coding': {
            'apps': ['Terminal' if platform.system() == 'Darwin' else 'cmd', 'Notes' if platform.system() == 'Darwin' else 'notepad'],
            'urls': ['https://github.com', 'https://stackoverflow.com', 'https://youtube.com/feed/music']
        },
        'content_creation': {
            'apps': ['Photos'],
            'urls': ['https://studio.youtube.com', 'https://x.com']
        },
        'research': {
            'apps': ['Notes' if platform.system() == 'Darwin' else 'notepad'],
            'urls': ['https://google.com']
        },
        'relax': {
            'apps': ['Music' if platform.system() == 'Darwin' else 'spotify'],
            'urls': ['https://youtube.com']
        },
        'design': {
            'apps': [],
            'urls': ['https://figma.com', 'https://dribbble.com', 'https://pinterest.com']
        },
        'finance': {
            'apps': [],
            'urls': ['https://tradingview.com', 'https://finance.yahoo.com']
        },
        'gaming': {
            'apps': [],
            'urls': ['https://twitch.tv', 'https://gaming.youtube.com', 'https://discord.com/app']
        },
        'web_dev': {
            'apps': ['Terminal' if platform.system() == 'Darwin' else 'cmd'],
            'urls': ['https://github.com', 'https://stackoverflow.com', 'http://localhost:3000']
        },
        'custom': {
            'apps': [],
            'urls': []
        }
    }
    
    if mode not in workflows:
        mode = 'custom'
        
    workflow = workflows[mode]
    final_urls = workflow['urls'] + dynamic_urls
    
    try:
        # Open apps
        for app in workflow['apps']:
            open_application(app)
            
        # Open URLs
        if final_urls:
            if platform.system() == "Darwin":
                urls_str = '", "'.join(final_urls)
                script = f'''
                tell application "Google Chrome"
                    activate
                    if (count every window) = 0 then
                        make new window
                    end if
                    set urlList to {{"{urls_str}"}}
                    repeat with u in urlList
                        tell front window
                            make new tab with properties {{URL:u}}
                        end tell
                    end repeat
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
            else:
                for url in final_urls:
                    webbrowser.open(url)
            
        return f"Successfully set up '{mode}' workspace. Launched {len(workflow['apps'])} apps and loaded {len(final_urls)} browser tabs."
    except Exception as e:
        return f"Error setting up workspace: {str(e)}"

@mcp.tool()
def chrome_control(action: str, url: str = None) -> str:
    """
    Advanced control for Google Chrome via AppleScript (macOS only).
    Actions supported:
    - 'open_tab': Opens a new tab with the specified url.
    - 'extract_text': Extracts all readable text from the currently active tab in Chrome.
    """
    if platform.system() != "Darwin":
        return f"Chrome control action '{action}' is only supported on macOS, sir."
        
    try:
        if action == 'open_tab':
            if not url:
                return "URL is required for open_tab action."
            if not url.startswith('http'):
                url = 'https://' + url
            script = f'''
            tell application "Google Chrome"
                activate
                if (count every window) = 0 then
                    make new window
                end if
                tell front window
                    make new tab with properties {{URL:"{url}"}}
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            return f"Successfully opened {url} in a new Chrome tab."
            
        elif action == 'extract_text':
            script = '''
            tell application "Google Chrome"
                set activeTab to active tab of front window
                set pageText to execute activeTab javascript "document.body.innerText;"
                return pageText
            end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
            text = result.stdout.strip()
            
            if not text or text == "missing value":
                return "Could not extract text. The page might be empty, or Chrome is not open."
                
            if len(text) > 5000:
                text = text[:5000] + "\n...[Content truncated]"
                
            return f"Extracted text from current tab:\n\n{text}"
            
        else:
            return f"Unknown action: {action}. Supported actions are 'open_tab' and 'extract_text'."
            
    except Exception as e:
        return f"Error controlling Chrome: {str(e)}"

@mcp.tool()
def search_web(query: str) -> str:
    """Performs a Google search for the given query and opens results in browser."""
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    return open_url(url)

@mcp.tool()
def research_topic(query: str, open_in_browser: bool = True) -> str:
    """
    Researches a topic by searching the web, opening results and returning text.
    Use this when the user asks about something you don't know or need current information about.
    """
    from bs4 import BeautifulSoup
    import re
    
    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        search_response = requests.get(search_url, headers=headers, timeout=10)
        search_soup = BeautifulSoup(search_response.text, 'html.parser')
        
        result_links = []
        for a_tag in search_soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith('/url?q='):
                clean_url = href.split('/url?q=')[1].split('&')[0]
                if not any(skip in clean_url for skip in ['google.com', 'youtube.com', 'accounts.google', 'support.google', 'maps.google']):
                    result_links.append(clean_url)
        
        if not result_links:
            # Fallback to DuckDuckGo
            ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            ddg_response = requests.get(ddg_url, headers=headers, timeout=10)
            ddg_soup = BeautifulSoup(ddg_response.text, 'html.parser')
            for a_tag in ddg_soup.find_all('a', class_='result__a', href=True):
                href = a_tag['href']
                if href.startswith('http'):
                    result_links.append(href)
        
        if not result_links:
            if open_in_browser:
                webbrowser.open(search_url)
            return f"I searched for '{query}' but couldn't extract specific results. I've opened the search page for you, sir."
        
        top_url = result_links[0]
        if open_in_browser:
            webbrowser.open(top_url)
        
        try:
            page_response = requests.get(top_url, headers=headers, timeout=10)
            page_response.raise_for_status()
            page_soup = BeautifulSoup(page_response.text, 'html.parser')
            
            for tag in page_soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
                tag.decompose()
            
            main_content = page_soup.find('main') or page_soup.find('article') or page_soup.find('div', class_=re.compile(r'content|article|post|entry|text', re.I))
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                paragraphs = page_soup.find_all('p')
                text = '\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
            
            lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 10]
            clean_text = '\n'.join(lines[:40])
            
            if len(clean_text) > 3000:
                clean_text = clean_text[:3000] + "..."
            
            if not clean_text:
                return f"I've opened {top_url} in your browser, sir, but couldn't extract readable text. Please review it visually."
            
            return f"Source: {top_url}\n\n{clean_text}"
            
        except Exception as scrape_err:
            return f"I've opened {top_url} in your browser, sir. However, I wasn't able to read the page content automatically: {str(scrape_err)}"
    
    except Exception as e:
        try:
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        except:
            pass
        return f"I encountered an issue researching '{query}': {str(e)}. I've opened a search page for you instead, sir."

@mcp.tool()
def control_volume(level: int) -> str:
    """Sets the system volume (0-100)."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
            return f"System volume set to {level} percent, sir."
        else:
            return "Volume control is currently only supported on macOS."
    except Exception as e:
        return f"Error setting volume: {str(e)}"

@mcp.tool()
def get_battery_info() -> str:
    """Returns system battery percentage and status."""
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return "No battery detected (likely running on AC desktop power), sir."
        
        percent = battery.percent
        plugged = "plugged in" if battery.power_plugged else "on battery power"
        
        seconds_left = battery.secsleft
        if seconds_left == psutil.POWER_TIME_UNLIMITED:
            time_str = "charging/unlimited"
        elif seconds_left == psutil.POWER_TIME_UNKNOWN:
            time_str = "unknown time remaining"
        else:
            hours = seconds_left // 3600
            mins = (seconds_left % 3600) // 60
            time_str = f"{hours}h {mins}m remaining"
            
        return f"Battery Status: {percent}% ({plugged}), {time_str}, sir."
    except Exception as e:
        return f"Error checking battery: {str(e)}"

@mcp.tool()
def lock_screen() -> str:
    """Immediately locks the screen."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'])
            return "Locking the station now, sir."
        elif platform.system() == "Windows":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Locking the Windows workstation, sir."
        else:
            return f"Lock screen not supported on {platform.system()}."
    except Exception as e:
        return f"Error locking screen: {str(e)}"

@mcp.tool()
def get_top_processes() -> str:
    """Returns the top 5 processes consuming CPU."""
    try:
        procs = sorted(psutil.process_iter(['name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'] or 0, reverse=True)
        output = "Top CPU Consumers:\n"
        for p in procs[:5]:
            output += f"- {p.info['name']}: {p.info['cpu_percent'] or 0}%\n"
        return output
    except Exception as e:
        return f"Error fetching processes: {str(e)}"

@mcp.tool()
def take_screenshot(path: str = "~/Desktop/jarvis_screenshot.png") -> str:
    """Takes a screenshot of the screen and saves it."""
    try:
        expanded_path = os.path.expanduser(path)
        if platform.system() == "Darwin":
            subprocess.run(["screencapture", expanded_path])
            return f"Screenshot saved successfully to {expanded_path}, sir."
        else:
            try:
                import pyautogui
                img = pyautogui.screenshot()
                img.save(expanded_path)
                return f"Screenshot saved successfully via pyautogui to {expanded_path}, sir."
            except ImportError:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(expanded_path)
                return f"Screenshot saved successfully via PIL to {expanded_path}, sir."
    except Exception as e:
        return f"Failed to take screenshot: {str(e)}"

@mcp.tool()
def get_clipboard() -> str:
    """Reads the current text from the clipboard."""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True)
            return result.stdout
        elif platform.system() == "Windows":
            result = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], capture_output=True, text=True)
            return result.stdout.strip()
        else:
            return "Clipboard read not supported on this OS."
    except Exception as e:
        return f"Error reading clipboard: {str(e)}"

@mcp.tool()
def set_clipboard(text: str) -> str:
    """Writes text to the clipboard."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text, text=True)
            return "Text copied to clipboard successfully, sir."
        elif platform.system() == "Windows":
            subprocess.run(["clip"], input=text, text=True)
            return "Text copied to Windows clipboard successfully, sir."
        else:
            return "Clipboard write not supported on this OS."
    except Exception as e:
        return f"Error setting clipboard: {str(e)}"

@mcp.tool()
def get_wifi_info() -> str:
    """Retrieves current Wi-Fi network information and connection strength."""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"], capture_output=True, text=True)
            return result.stdout
        elif platform.system() == "Windows":
            result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
            return result.stdout
        else:
            return "Wi-Fi info not supported on this OS."
    except Exception as e:
        return f"Error fetching Wi-Fi info: {str(e)}"

@mcp.tool()
def list_open_ports() -> str:
    """Lists all active network ports currently listening on the machine."""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run("lsof -i -P | grep LISTEN", shell=True, capture_output=True, text=True)
            return result.stdout if result.stdout else "No listening ports found."
        elif platform.system() == "Windows":
            result = subprocess.run("netstat -ano | findstr LISTENING", shell=True, capture_output=True, text=True)
            return result.stdout if result.stdout else "No listening ports found."
        else:
            return "Port listing not supported on this OS."
    except Exception as e:
        return f"Error listing ports: {str(e)}"

@mcp.tool()
def kill_port(port: int) -> str:
    """Kills the process running on a specific port."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True)
            return f"Terminated the process running on port {port}, sir."
        elif platform.system() == "Windows":
            result = subprocess.run(f"netstat -ano | findstr LISTENING | findstr :{port}", shell=True, capture_output=True, text=True)
            output = result.stdout.strip()
            if not output:
                return f"No process found listening on port {port}."
            lines = output.split('\n')
            pids = set()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
            killed = []
            for pid in pids:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                killed.append(pid)
            return f"Terminated processes with PIDs {', '.join(killed)} running on port {port}, sir."
        else:
            return "Port termination not supported on this OS."
    except Exception as e:
        return f"Error killing port {port}: {str(e)}"

@mcp.tool()
def docker_status() -> str:
    """Lists all running Docker containers and their status."""
    try:
        result = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"], capture_output=True, text=True)
        return result.stdout if result.stdout else "No Docker containers currently running."
    except Exception as e:
        return "Error fetching Docker status. Is Docker Desktop running?"

@mcp.tool()
def search_codebase(pattern: str, path: str = ".") -> str:
    """Searches for a text pattern in code files (.py, .js, .ts) in a given path."""
    try:
        if platform.system() == "Darwin":
            cmd = f"grep -r --include='*.py' --include='*.js' --include='*.ts' -n '{pattern}' {path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout[:2000] if result.stdout else f"No matches found for '{pattern}'."
        else:
            import os
            matches = []
            target_exts = ('.py', '.js', '.ts')
            for root, dirs, files in os.walk(path):
                if any(x in root for x in ('node_modules', '.git', '.venv', '__pycache__')):
                    continue
                for file in files:
                    if file.endswith(target_exts):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for i, line in enumerate(f, 1):
                                    if pattern in line:
                                        matches.append(f"{file_path}:{i}: {line.strip()}")
                                        if len(matches) >= 50:
                                            break
                        except Exception:
                            pass
                if len(matches) >= 50:
                    break
            
            output = '\n'.join(matches[:40])
            if len(matches) > 40:
                output += "\n...[Additional results truncated]"
            return output if output else f"No matches found for '{pattern}'."
    except Exception as e:
        return f"Error searching codebase: {str(e)}"

@mcp.tool()
def open_famous_news_website(channel: str = "cnn") -> str:
    """
    Opens the website of a famous news channel in the default browser.
    Valid channels: cnn, bbc, fox, al jazeera, nbc, bloomberg, reuters.
    """
    news_urls = {
        "cnn": "https://www.cnn.com",
        "bbc": "https://www.bbc.com/news",
        "fox": "https://www.foxnews.com",
        "al jazeera": "https://www.aljazeera.com",
        "aljazeera": "https://www.aljazeera.com",
        "nbc": "https://www.nbcnews.com",
        "bloomberg": "https://www.bloomberg.com",
        "reuters": "https://www.reuters.com",
        "sky": "https://news.sky.com"
    }
    
    url = news_urls.get(channel.lower())
    if not url:
        return f"I don't have '{channel}' in my primary news database, sir. Try CNN, BBC, or Reuters."
    
    try:
        webbrowser.open(url)
        return f"Opening {channel.upper()} in your browser now, sir. Fetching the latest news."
    except Exception as e:
        return f"Error opening the news website: {str(e)}"

if __name__ == "__main__":
    mcp.run()
