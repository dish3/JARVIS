#!/usr/bin/env python3
"""
JARVIS Test Suite
Runs unit and integration tests for all backend modules:
Router, Memory, FileTool, TerminalTool, BrowserTool, Orchestrator, and Planner.
"""

import os
import sys
import unittest
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add VirtualAssistant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from router import Router
from memory import Memory, _MEMORY_FILE, _MAX_INTERACTIONS
from tools.file_tool import FileTool
from tools.terminal_tool import TerminalTool
from tools.browser_tool import BrowserTool
from orchestrator import Orchestrator
from planner import Planner


class TestRouter(unittest.TestCase):
    """Unit tests for the Router command detection and regex patterns"""

    def setUp(self):
        self.router = Router()

    def test_browser_open_routing(self):
        # Open URL queries
        queries = [
            ("open google.com", "browser", "open", {"url": "https://google.com"}),
            ("visit http://github.com", "browser", "open", {"url": "https://github.com"}),
            ("browse youtube in chrome", "browser", "open", {"url": "https://youtube.com", "browser": "chrome"}),
            ("launch chrome yahoo.com", "browser", "open", {"url": "https://yahoo.com"}),
        ]
        for query, expected_tool, expected_action, expected_params in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"])
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                # Check url is formatted and matches
                self.assertEqual(res["parameters"]["url"], expected_params["url"])
                if "browser" in expected_params:
                    self.assertEqual(res["parameters"]["browser"], expected_params["browser"])

    def test_browser_search_routing(self):
        queries = [
            ("search google for how to learn python", "browser", "search", {"query": "how to learn python"}),
            ("google machine learning tutorials", "browser", "search", {"query": "machine learning tutorials"}),
            ("search google for quantum computing", "browser", "search", {"query": "quantum computing"}),
            ("search web for local restaurants", "browser", "search", {"query": "local restaurants"}),
        ]
        for query, expected_tool, expected_action, expected_params in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"])
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                self.assertEqual(res["parameters"]["query"], expected_params["query"])

    def test_file_routing(self):
        queries = [
            ("read config.json", "file", "read", {"path": "config.json"}),
            ("view file src/main.py", "file", "read", {"path": "src/main.py"}),
            ("create file notes.txt with content clean code", "file", "write", {"path": "notes.txt", "content": "clean code"}),
            ("save file output.log content status ok", "file", "write", {"path": "output.log", "content": "status ok"}),
            ("list files", "file", "list", {"path": "."}),
            ("show files in docs/", "file", "list", {"path": "docs/"}),
        ]
        for query, expected_tool, expected_action, expected_params in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"])
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                self.assertEqual(res["parameters"]["path"], expected_params["path"])
                if "content" in expected_params:
                    self.assertEqual(res["parameters"]["content"], expected_params["content"])

    def test_terminal_routing(self):
        queries = [
            ("run python script.py", "terminal", "execute"),
            ("execute npm run build", "terminal", "execute"),
            ("cmd dir /w", "terminal", "execute"),
            ("python -m pip install pytest", "terminal", "execute"),
            ("npm start", "terminal", "execute"),
        ]
        for query, expected_tool, expected_action in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"])
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                self.assertEqual(res["parameters"]["command"], query)

    def test_git_routing(self):
        queries = [
            ("git status", "git", "status", {}),
            ("show git status", "git", "status", {}),
            ("git add main.py", "git", "add", {"path": "main.py"}),
            ("git commit with message \"initial commit\"", "git", "commit", {"message": "initial commit"}),
            ("git commit changes and push with message \"feat: login\"", "git", "commit", {"message": "feat: login"}),
            ("git push origin main", "git", "push", {"remote": "origin", "branch": "main"}),
            ("push to github", "git", "push", {"remote": "github", "branch": None}),
            ("git pull origin dev", "git", "pull", {"remote": "origin", "branch": "dev"}),
            ("git log last 10", "git", "log", {"count": 10}),
            ("show git log", "git", "log", {"count": 5}),
        ]
        for query, expected_tool, expected_action, expected_params in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"], f"Failed to match command for: {query}")
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                for k, v in expected_params.items():
                    self.assertEqual(res["parameters"][k], v)

    def test_linkedin_routing(self):
        queries = [
            ("post to linkedin hello world", "linkedin", "post", {"text": "hello world"}),
            ("linkedin post hello | image C:\\image.png", "linkedin", "post", {"text": "hello", "image_path": "C:\\image.png"}),
            ("delete my last linkedin post", "linkedin", "delete", {}),
            ("remove linkedin post", "linkedin", "delete", {}),
        ]
        for query, expected_tool, expected_action, expected_params in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"])
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                for k, v in expected_params.items():
                    self.assertEqual(res["parameters"][k], v)

    def test_vscode_routing(self):
        query = "open main.py in vscode"
        res = self.router.route(query)
        self.assertTrue(res["is_command"])
        self.assertEqual(res["command_type"], "vscode")
        self.assertEqual(res["action"], "open")
        self.assertEqual(res["parameters"]["path"], "main.py")

    def test_image_generation_routing(self):
        queries = [
            ("generate an image of a red cat", "browser", "generate_image", {"prompt": "a red cat"}),
            ("create a picture of a sunset", "browser", "generate_image", {"prompt": "a sunset"}),
            ("draw a spaceship", "browser", "generate_image", {"prompt": "spaceship"}),
        ]
        for query, expected_tool, expected_action, expected_params in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertTrue(res["is_command"])
                self.assertEqual(res["command_type"], expected_tool)
                self.assertEqual(res["action"], expected_action)
                self.assertEqual(res["parameters"]["prompt"], expected_params["prompt"])

    def test_no_command_matched(self):
        queries = [
            "hello jarvis",
            "tell me a joke",
            "sing a song",
            "how do I learn programming",
        ]
        for query in queries:
            with self.subTest(query=query):
                res = self.router.route(query)
                self.assertFalse(res["is_command"])
                self.assertIsNone(res["command_type"])


class TestMemory(unittest.TestCase):
    """Unit tests for the Memory storage system"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_path = Path(self.temp_dir) / 'memory.json'
        
        # Patch the module-level _MEMORY_FILE variable
        self.patcher = patch('memory._MEMORY_FILE', self.memory_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_store_and_load_interactions(self):
        mem = Memory()
        mem.store_interaction("goal 1", "result 1")
        mem.store_interaction("goal 2", "result 2")
        mem.store_fact("user", "Disha")
        
        # Verify saved in memory
        self.assertEqual(len(mem.interactions), 2)
        self.assertEqual(mem.get_fact("user"), "Disha")
        
        # Verify persistence on disk by loading fresh instance
        mem2 = Memory()
        self.assertEqual(len(mem2.interactions), 2)
        self.assertEqual(mem2.interactions[0]["goal"], "goal 1")
        self.assertEqual(mem2.interactions[1]["result"], "result 2")
        self.assertEqual(mem2.get_fact("user"), "Disha")

    def test_trim_interactions_limit(self):
        mem = Memory()
        # Patch limit to something small for testing
        with patch('memory._MAX_INTERACTIONS', 5):
            for i in range(10):
                mem.store_interaction(f"goal {i}", f"result {i}")
            
            self.assertEqual(len(mem.interactions), 5)
            self.assertEqual(mem.interactions[0]["goal"], "goal 5")
            self.assertEqual(mem.interactions[-1]["goal"], "goal 9")

    def test_corrupt_json_handling(self):
        # Create invalid JSON file
        self.memory_path.write_text("{ corrupt json ...", encoding='utf-8')
        
        mem = Memory()
        # Should initialize with empty cache and back up corrupt file
        self.assertEqual(len(mem.interactions), 0)
        self.assertEqual(len(mem.user_facts), 0)
        
        backup_path = self.memory_path.with_suffix('.json.bak')
        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.read_text(encoding='utf-8'), "{ corrupt json ...")

    def test_clear_memory(self):
        mem = Memory()
        mem.store_interaction("test", "result")
        mem.store_fact("test", "fact")
        mem.clear()
        
        self.assertEqual(len(mem.interactions), 0)
        self.assertEqual(len(mem.user_facts), 0)
        
        mem2 = Memory()
        self.assertEqual(len(mem2.interactions), 0)


class TestFileTool(unittest.TestCase):
    """Unit and Integration tests for FileTool operations"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_tool = FileTool()
        
        # Set cwd to temp dir so relative paths go here
        self.orig_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.temp_dir)

    def test_write_and_read_file(self):
        # Test writing
        res_write = self.file_tool.write("test.txt", "hello JARVIS")
        self.assertIn("written successfully", res_write)
        
        # Test reading
        res_read = self.file_tool.read("test.txt")
        self.assertEqual(res_read, "hello JARVIS")

    def test_append_file(self):
        self.file_tool.write("test.txt", "hello")
        res_append = self.file_tool.execute({
            "action": "append",
            "path": "test.txt",
            "content": " world"
        })
        self.assertIn("Appended to", res_append)
        
        res_read = self.file_tool.read("test.txt")
        self.assertEqual(res_read, "hello world")

    def test_list_files(self):
        self.file_tool.write("a.txt", "content a")
        self.file_tool.write("b.txt", "content b")
        os.makedirs("subdir", exist_ok=True)
        self.file_tool.write("subdir/c.txt", "content c")
        
        res_list = self.file_tool.list_files(".")
        self.assertIn("[FILE] a.txt", res_list)
        self.assertIn("[FILE] b.txt", res_list)
        self.assertIn("[DIR]  subdir", res_list)

    def test_read_missing_file(self):
        res = self.file_tool.read("non_existent.txt")
        self.assertIn("Error: File not found", res)

    def test_path_validation_traversal_prevention(self):
        # Validated path should still work but normalizes directory traversals
        path = "dir/../../outside.txt"
        validated = self.file_tool._validate_path(path)
        expected = os.path.realpath(os.path.join(self.temp_dir, "..", "outside.txt"))
        self.assertEqual(validated, expected)


class TestTerminalTool(unittest.TestCase):
    """Unit tests for the TerminalTool execution and security filters"""

    def setUp(self):
        self.tool = TerminalTool()

    def test_is_safe_allowlist(self):
        safe_commands = [
            "echo hello",
            "python --version",
            "git status",
            "node -v",
            "npm -v",
            "pip list",
            "ls -la",
            "dir /w",
        ]
        for cmd in safe_commands:
            self.assertTrue(self.tool._is_safe(cmd), f"Command should be safe: {cmd}")

    def test_is_safe_blocklist(self):
        unsafe_commands = [
            "rm -rf /",
            "del /s /q C:\\",
            "shutdown -s -t 0",
            "reboot",
            "fdisk /mbr",
            "format c:",
        ]
        for cmd in unsafe_commands:
            self.assertFalse(self.tool._is_safe(cmd), f"Command should be blocked: {cmd}")

    def test_is_safe_unknown(self):
        # Unknown cmd should be blocked
        self.assertFalse(self.tool._is_safe("some_random_executable -arg"))

    def test_execute_echo(self):
        res = self.tool.execute("echo test_output_123")
        self.assertIn("test_output_123", res)

    def test_execute_blocked(self):
        res = self.tool.execute("shutdown -s -t 0")
        self.assertIn("Error: Command not allowed", res)


class TestBrowserTool(unittest.TestCase):
    """Unit tests for BrowserTool parameter checks"""

    def setUp(self):
        self.tool = BrowserTool()

    @patch('webbrowser.open')
    def test_open_url_default(self, mock_web_open):
        res = self.tool.open_url("github.com")
        mock_web_open.assert_called_once_with("https://github.com")
        self.assertIn("Opened URL: https://github.com", res)

    @patch('webbrowser.open')
    def test_search_default(self, mock_web_open):
        res = self.tool.search("python language")
        mock_web_open.assert_called_once_with("https://www.google.com/search?q=python%20language")
        self.assertIn("Searching google for: python language", res)

    def test_open_app_missing(self):
        res = self.tool.open_app("non_existent_app_123")
        self.assertIn("Error: Unknown app", res)


class TestPlanner(unittest.TestCase):
    """Unit tests for Planner error and fallback parsing"""

    def setUp(self):
        self.planner = Planner()

    def test_parse_response_tool(self):
        response_text = """
TOOL: terminal
ACTION: execute
PARAMETERS: {"command": "npm install"}
RESPONSE: I will install npm packages now.
"""
        res = self.planner._parse_response(response_text, "install packages")
        self.assertTrue(res["requires_tool"])
        self.assertEqual(res["tool_type"], "terminal")
        self.assertEqual(res["action"], "execute")
        self.assertEqual(res["parameters"], {"command": "npm install"})
        self.assertEqual(res["response"], "I will install npm packages now.")

    def test_parse_response_no_tool(self):
        response_text = """
TOOL: none
ACTION: none
PARAMETERS: NONE
RESPONSE: Python is a high-level programming language.
"""
        res = self.planner._parse_response(response_text, "what is python")
        self.assertFalse(res["requires_tool"])
        self.assertIsNone(res["tool_type"])
        self.assertEqual(res["response"], "Python is a high-level programming language.")

    def test_unavailable_response(self):
        res = self.planner._unavailable_response("test goal")
        self.assertFalse(res["requires_tool"])
        self.assertIn("Ollama is not running", res["response"])


class TestOrchestrator(unittest.TestCase):
    """Integration tests for the Orchestrator routing and tool execution"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_path = Path(self.temp_dir) / 'memory.json'
        
        # Patch Memory path and BrowserTool web open
        self.patchers = [
            patch('memory._MEMORY_FILE', self.memory_path),
            patch('webbrowser.open', MagicMock())
        ]
        for p in self.patchers:
            p.start()
            
        self.orchestrator = Orchestrator()
        # Direct FileTool to the temp directory
        self.orchestrator.file_tool.base_path = self.temp_dir

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        shutil.rmtree(self.temp_dir)

    def test_orchestrator_router_routing_flow(self):
        # Goal routed directly by Router
        goal = "create file note.txt with content testing orchestrator"
        res = self.orchestrator.process_goal(goal)
        
        self.assertTrue(res["success"])
        self.assertEqual(res["tool_used"], "file")
        self.assertTrue(res["memory_updated"])
        self.assertIn("[COMMAND EXECUTED] file", res["logs"])
        
        # Verify the file was created
        filepath = Path(self.orchestrator.file_tool._validate_path("note.txt"))
        self.assertTrue(filepath.exists())
        self.assertEqual(filepath.read_text(encoding='utf-8'), "testing orchestrator")

    @patch('planner.Planner._is_ollama_available', return_value=False)
    def test_orchestrator_planner_fallback_flow(self, mock_is_available):
        # Goal that requires planner, but Ollama is offline
        goal = "explain string theory in detail"
        res = self.orchestrator.process_goal(goal)
        
        self.assertTrue(res["success"])
        self.assertIn("Ollama is not running", res["result"])


class TestVoiceComponents(unittest.TestCase):
    """Test importing and initializing voice listener and output"""

    def test_voice_output_initialization(self):
        try:
            from voice_output import VoiceOutput
            # Initialize with low volume and fast rate
            tts = VoiceOutput(rate=200, volume=0.5)
            self.assertIsNotNone(tts)
        except Exception as e:
            # Let it pass if OS has no TTS engine installed
            self.skipTest(f"Skipped because voice TTS initialization failed: {e}")

    def test_voice_listener_initialization(self):
        try:
            from voice_listener import VoiceListener
            # FastWhisper check
            listener = VoiceListener(model_size='tiny')
            self.assertIsNotNone(listener)
        except Exception as e:
            # Whisper model initialization might require large downloads/Cuda
            self.skipTest(f"Skipped voice listener initialization: {e}")


class TestLinkedInTool(unittest.TestCase):
    """Unit tests for LinkedInTool session and credential logic"""

    def setUp(self):
        from tools.linkedin_tool import LinkedInTool
        self.tool = LinkedInTool()

    @patch.dict(os.environ, {"LINKEDIN_EMAIL": "example@example.com"}, clear=True)
    def test_missing_credentials_handling(self):
        # Email has example.com -> should reject
        res = self.tool.post("test")
        self.assertIn("Error: LinkedIn credentials not set", res)

    def test_session_expired_by_url(self):
        mock_page = MagicMock()
        
        # Expired cases
        expired_urls = [
            "https://www.linkedin.com/login",
            "https://www.linkedin.com/checkpoint/rp/request-password-reset",
            "https://www.linkedin.com/uas/authenticate",
            "https://www.linkedin.com/feed/session-expired"
        ]
        for url in expired_urls:
            mock_page.url = url
            self.assertTrue(self.tool._is_session_expired(mock_page), f"Should be expired: {url}")

        # Active case
        mock_page.url = "https://www.linkedin.com/feed/"
        # Mock #username locator to return not visible
        mock_locator = MagicMock()
        mock_locator.is_visible.return_value = False
        mock_page.locator.return_value = mock_locator
        
        self.assertFalse(self.tool._is_session_expired(mock_page))

    def test_session_expired_by_login_form_visible(self):
        mock_page = MagicMock()
        mock_page.url = "https://www.linkedin.com/feed/"
        
        # Mock #username locator to be visible (signals session expired / auth request)
        mock_locator = MagicMock()
        mock_locator.is_visible.return_value = True
        mock_page.locator.return_value = mock_locator
        
        self.assertTrue(self.tool._is_session_expired(mock_page))


if __name__ == '__main__':
    unittest.main()
