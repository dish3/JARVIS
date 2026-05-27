#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add VirtualAssistant to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.linkedin_tool import LinkedInTool

text = "Hello connections! Excited to share this abstract representation of AI intelligence created via my agentic capabilities. Automated posting powered by JARVIS AI Assistant. #AI #Innovation #Technology #Automation"
image_path = "E:/PROJECTS/JARVIS/generated_images/linkedin_post_image.png"

print("Initializing LinkedInTool...")
tool = LinkedInTool()
print(f"Posting text: {text}")
print(f"Image path: {image_path}")

result = tool.post(text, image_path)
print("=" * 60)
print("RESULT OF POST OPERATION:")
print(result)
print("=" * 60)
