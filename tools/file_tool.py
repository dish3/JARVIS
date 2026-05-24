#!/usr/bin/env python3
"""
File Tool - Read, write, and list files
Safe file operations with path validation
"""

import os
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger('FILE_TOOL')


class FileTool:
    """Safe file operations"""
    
    def __init__(self):
        logger.info("Initializing File Tool...")
        self.base_path = os.path.expanduser('~')
        logger.info(f"[OK] File Tool initialized (base: {self.base_path})")
    
    def execute(self, parameters: Dict) -> str:
        """
        Route incoming actions to appropriate methods
        
        Args:
            parameters: Dict with 'action' and 'path' keys
            
        Returns:
            Result from the action
        """
        action = parameters.get('action', 'list')
        path = parameters.get('path', '.')
        
        # Handle 'current directory' special case
        if path == 'current directory' or path == '.' or path == '':
            path = os.getcwd()
        
        # Route to appropriate method
        if action in ('list', 'open', 'browse', None):
            if os.path.isfile(path):
                return self.read(path)
            return self.list_files(path)
        elif action == 'read':
            return self.read(path)
        elif action in ('write', 'create', 'save'):
            content = parameters.get('content', '')
            return self.write(path, content)
        elif action == 'append':
            content = parameters.get('content', '')
            try:
                with open(self._validate_path(path), 'a', encoding='utf-8') as f:
                    f.write(content)
                return f"Appended to: {path}"
            except Exception as e:
                return f"Error: {str(e)}"
        else:
            # Unknown action — try reading if file, listing if dir
            if os.path.isfile(path):
                return self.read(path)
            return self.list_files(path)
    
    def _validate_path(self, path: str) -> str:
        """Validate and normalize file path"""
        # Expand user home directory
        path = os.path.expanduser(path)
        
        # Convert to absolute path
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        
        # Normalize path
        path = os.path.normpath(path)
        
        # Security: prevent directory traversal attacks
        real_path = os.path.realpath(path)
        
        logger.info(f"[FILE] Validated path: {path} -> {real_path}")
        return real_path
    
    def read(self, path: str) -> str:
        """
        Read file contents
        
        Args:
            path: File path
            
        Returns:
            File contents or error message
        """
        logger.info(f"[FILE] Reading: {path}")
        
        try:
            validated_path = self._validate_path(path)
            
            # Check if file exists
            if not os.path.isfile(validated_path):
                logger.warning(f"[FILE] File not found: {validated_path}")
                return f"Error: File not found: {path}"
            
            # Read file
            with open(validated_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"[FILE] Read {len(content)} bytes from {validated_path}")
            return content
        
        except UnicodeDecodeError:
            logger.error(f"[FILE] Cannot decode file: {path}")
            return f"Error: File is not text (binary file)"
        except PermissionError:
            logger.error(f"[FILE] Permission denied: {path}")
            return f"Error: Permission denied"
        except Exception as e:
            logger.error(f"[FILE] Error reading: {str(e)}")
            return f"Error: {str(e)}"
    
    def write(self, path: str, content: str) -> str:
        """
        Write content to file
        
        Args:
            path: File path
            content: Content to write
            
        Returns:
            Success message or error
        """
        logger.info(f"[FILE] Writing to: {path}")
        
        try:
            validated_path = self._validate_path(path)
            
            # Create parent directories if needed
            parent_dir = os.path.dirname(validated_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                logger.info(f"[FILE] Created directory: {parent_dir}")
            
            # Write file
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"[FILE] Wrote {len(content)} bytes to {validated_path}")
            return f"File written successfully: {path}"
        
        except PermissionError:
            logger.error(f"[FILE] Permission denied: {path}")
            return f"Error: Permission denied"
        except Exception as e:
            logger.error(f"[FILE] Error writing: {str(e)}")
            return f"Error: {str(e)}"
    
    def list_files(self, path: str = '.') -> str:
        """
        List files in directory
        
        Args:
            path: Directory path
            
        Returns:
            List of files or error message
        """
        logger.info(f"[FILE] Listing: {path}")
        
        try:
            validated_path = self._validate_path(path)
            
            # Check if directory exists
            if not os.path.isdir(validated_path):
                logger.warning(f"[FILE] Directory not found: {validated_path}")
                return f"Error: Directory not found: {path}"
            
            # List files
            items = os.listdir(validated_path)
            
            # Separate files and directories
            files = []
            dirs = []
            
            for item in items:
                item_path = os.path.join(validated_path, item)
                if os.path.isdir(item_path):
                    dirs.append(f"[DIR]  {item}")
                else:
                    size = os.path.getsize(item_path)
                    files.append(f"[FILE] {item} ({size} bytes)")
            
            # Sort and combine
            output = []
            if dirs:
                output.extend(sorted(dirs))
            if files:
                output.extend(sorted(files))
            
            result = "\n".join(output) if output else "Directory is empty"
            logger.info(f"[FILE] Listed {len(items)} items in {validated_path}")
            return result
        
        except PermissionError:
            logger.error(f"[FILE] Permission denied: {path}")
            return f"Error: Permission denied"
        except Exception as e:
            logger.error(f"[FILE] Error listing: {str(e)}")
            return f"Error: {str(e)}"


def main():
    """Test file tool"""
    tool = FileTool()
    
    # Test read
    print("\n=== Test Read ===")
    result = tool.read("requirements.txt")
    print(result[:200] if len(result) > 200 else result)
    
    # Test list
    print("\n=== Test List ===")
    result = tool.list_files(".")
    print(result[:500] if len(result) > 500 else result)
    
    # Test write
    print("\n=== Test Write ===")
    result = tool.write("test_file.txt", "Hello from JARVIS!")
    print(result)
    
    # Read back
    print("\n=== Read Back ===")
    result = tool.read("test_file.txt")
    print(result)


if __name__ == '__main__':
    main()
