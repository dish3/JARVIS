#!/usr/bin/env python3
"""
Text Input - CLI text input handler
Reads user input from command line
"""

import logging
import sys
from typing import Optional

logger = logging.getLogger('TEXT_INPUT')


class TextInput:
    """Handle text input from CLI"""
    
    def __init__(self):
        logger.info("Initializing Text Input...")
        logger.info("✅ Text Input initialized")
    
    def get_input(self, prompt: str = "You: ") -> Optional[str]:
        """
        Get text input from user
        
        Args:
            prompt: Input prompt
            
        Returns:
            User input or None if error
        """
        logger.info(f"[INPUT] Waiting for input...")
        
        try:
            user_input = input(prompt).strip()
            
            if not user_input:
                logger.warning("[INPUT] Empty input")
                return None
            
            logger.info(f"[INPUT] Received: {user_input[:100]}...")
            return user_input
        
        except KeyboardInterrupt:
            logger.info("[INPUT] Interrupted by user")
            return None
        except EOFError:
            logger.info("[INPUT] EOF reached")
            return None
        except Exception as e:
            logger.error(f"[INPUT] Error: {str(e)}")
            return None
    
    def get_multiline_input(self, prompt: str = "Enter text (Ctrl+D to finish):\n") -> Optional[str]:
        """
        Get multiline text input
        
        Args:
            prompt: Input prompt
            
        Returns:
            User input or None if error
        """
        logger.info("[INPUT] Waiting for multiline input...")
        
        try:
            print(prompt)
            lines = []
            
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break
            
            text = "\n".join(lines).strip()
            
            if not text:
                logger.warning("[INPUT] Empty input")
                return None
            
            logger.info(f"[INPUT] Received {len(lines)} lines")
            return text
        
        except KeyboardInterrupt:
            logger.info("[INPUT] Interrupted by user")
            return None
        except Exception as e:
            logger.error(f"[INPUT] Error: {str(e)}")
            return None
    
    def get_choice(self, options: list, prompt: str = "Choose an option: ") -> Optional[str]:
        """
        Get user choice from options
        
        Args:
            options: List of options
            prompt: Input prompt
            
        Returns:
            Selected option or None
        """
        logger.info(f"[INPUT] Presenting {len(options)} options...")
        
        try:
            # Display options
            for i, option in enumerate(options, 1):
                print(f"{i}. {option}")
            
            # Get choice
            while True:
                choice = input(prompt).strip()
                
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(options):
                        selected = options[index]
                        logger.info(f"[INPUT] Selected: {selected}")
                        return selected
                    else:
                        print(f"Invalid choice. Please enter 1-{len(options)}")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        
        except KeyboardInterrupt:
            logger.info("[INPUT] Interrupted by user")
            return None
        except Exception as e:
            logger.error(f"[INPUT] Error: {str(e)}")
            return None


def main():
    """Test text input"""
    text_input = TextInput()
    
    # Test single line input
    print("\n=== Test Single Line Input ===")
    result = text_input.get_input("Enter a command: ")
    print(f"You entered: {result}")
    
    # Test choice
    print("\n=== Test Choice ===")
    options = ["Open Chrome", "Open Firefox", "Search Google", "Exit"]
    result = text_input.get_choice(options)
    print(f"You chose: {result}")


if __name__ == '__main__':
    main()
