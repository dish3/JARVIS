#!/usr/bin/env python3
"""
JARVIS Startup Script
Initializes all components and starts the system
"""

import sys
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('jarvis_startup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('STARTUP')


def print_banner():
    """Print JARVIS banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                    🤖 JARVIS AI ASSISTANT 🤖                 ║
║                                                               ║
║              Adaptive Real-time Intelligent Assistant         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_dependencies():
    """Check if all required dependencies are installed"""
    logger.info("Checking dependencies...")
    
    required = {
        'dotenv': 'python-dotenv',
        'requests': 'requests',
        'faster_whisper': 'faster-whisper',
        'pyttsx3': 'pyttsx3',
        'playwright': 'playwright',
    }
    
    missing = []
    
    for module, package in required.items():
        try:
            __import__(module)
            logger.info(f"✅ {package}")
        except ImportError:
            logger.warning(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        logger.error(f"\nMissing dependencies: {', '.join(missing)}")
        logger.error(f"Install with: pip install -r requirements.txt")
        return False
    
    logger.info("✅ All dependencies installed")
    return True


def check_ollama():
    """Check if Ollama is running"""
    logger.info("Checking Ollama...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            logger.info("✅ Ollama is running")
            return True
    except:
        pass
    
    logger.warning("⚠️ Ollama not running")
    logger.warning("Start Ollama with: ollama run phi3.5")
    return False


def initialize_components():
    """Initialize all JARVIS components"""
    logger.info("Initializing components...")
    
    try:
        from orchestrator import Orchestrator
        from voice_listener import VoiceListener
        from voice_output import VoiceOutput
        from text_input import TextInput
        
        logger.info("Initializing Orchestrator...")
        orchestrator = Orchestrator()
        
        logger.info("Initializing Voice Listener...")
        voice_listener = VoiceListener(model_size='base')
        
        logger.info("Initializing Voice Output...")
        voice_output = VoiceOutput(rate=150, volume=0.9)
        
        logger.info("Initializing Text Input...")
        text_input = TextInput()
        
        logger.info("✅ All components initialized")
        
        return {
            'orchestrator': orchestrator,
            'voice_listener': voice_listener,
            'voice_output': voice_output,
            'text_input': text_input,
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize components: {str(e)}")
        return None


def test_system(components):
    """Test system components"""
    logger.info("Testing system...")
    
    try:
        orchestrator = components['orchestrator']
        
        # Test a simple command
        logger.info("Testing command routing...")
        result = orchestrator.process_goal("open chrome")
        
        if result['success']:
            logger.info(f"✅ Command executed: {result['result']}")
        else:
            logger.warning(f"⚠️ Command failed: {result['result']}")
        
        logger.info("✅ System test completed")
        return True
    
    except Exception as e:
        logger.error(f"❌ System test failed: {str(e)}")
        return False


def main():
    """Main startup sequence"""
    print_banner()
    
    logger.info("=" * 60)
    logger.info("JARVIS STARTUP SEQUENCE")
    logger.info("=" * 60)
    
    # Step 1: Check dependencies
    if not check_dependencies():
        logger.error("Cannot proceed without dependencies")
        return False
    
    # Step 2: Check Ollama
    ollama_ok = check_ollama()
    if not ollama_ok:
        logger.warning("Continuing without Ollama (AI features limited)")
    
    # Step 3: Initialize components
    components = initialize_components()
    if not components:
        logger.error("Failed to initialize components")
        return False
    
    # Step 4: Test system
    if not test_system(components):
        logger.warning("System test failed, but continuing...")
    
    logger.info("=" * 60)
    logger.info("✅ JARVIS READY")
    logger.info("=" * 60)
    
    # Start interactive mode
    logger.info("\nStarting interactive mode...")
    logger.info("Type 'exit' to quit\n")
    
    text_input = components['text_input']
    orchestrator = components['orchestrator']
    voice_output = components['voice_output']
    
    while True:
        try:
            # Get user input
            user_input = text_input.get_input("You: ")
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                logger.info("Goodbye!")
                voice_output.speak("Goodbye!")
                break
            
            # Process goal
            logger.info(f"Processing: {user_input}")
            result = orchestrator.process_goal(user_input)
            
            # Output result
            if result['success']:
                response = result['result']
                print(f"JARVIS: {response}\n")
                voice_output.speak(response, wait=False)
            else:
                error = result['result']
                print(f"JARVIS: Error - {error}\n")
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"Error: {str(e)}\n")
    
    logger.info("JARVIS shutdown complete")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
