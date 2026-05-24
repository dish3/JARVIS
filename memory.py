#!/usr/bin/env python3
"""
JARVIS Memory - Session Storage (RAM)
Stores interactions, user facts, context
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger('MEMORY')


class Memory:
    """In-memory storage for interactions and context"""
    
    def __init__(self):
        logger.info("Initializing Memory...")
        
        self.interactions: List[Dict] = []
        self.user_facts: Dict[str, Any] = {}
        self.session_start = datetime.now()
        
        logger.info("[OK] Memory initialized")
    
    def store_interaction(self, goal: str, result: Any) -> None:
        """Store a goal-result interaction"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'goal': goal,
            'result': result,
        }
        
        self.interactions.append(interaction)
        logger.info(f"[MEMORY] Stored interaction #{len(self.interactions)}")
        
        # Keep only last 100 interactions
        if len(self.interactions) > 100:
            self.interactions = self.interactions[-100:]
    
    def store_fact(self, key: str, value: Any) -> None:
        """Store a user fact"""
        self.user_facts[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
        }
        logger.info(f"[MEMORY] Stored fact: {key} = {value}")
    
    def get_fact(self, key: str) -> Optional[Any]:
        """Retrieve a user fact"""
        if key in self.user_facts:
            return self.user_facts[key]['value']
        return None
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context for planner"""
        recent_interactions = self.interactions[-5:] if self.interactions else []
        
        return {
            'session_duration': str(datetime.now() - self.session_start),
            'total_interactions': len(self.interactions),
            'recent_interactions': recent_interactions,
            'user_facts': self.user_facts,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get memory summary"""
        return {
            'session_start': self.session_start.isoformat(),
            'total_interactions': len(self.interactions),
            'user_facts_count': len(self.user_facts),
            'memory_size_kb': len(json.dumps(self.interactions)) / 1024,
        }
    
    def clear(self) -> None:
        """Clear all memory"""
        logger.warning("[MEMORY] Clearing all memory")
        self.interactions = []
        self.user_facts = {}
        self.session_start = datetime.now()


def main():
    """Test memory"""
    memory = Memory()
    
    # Store interactions
    memory.store_interaction("open chrome", "Chrome opened successfully")
    memory.store_interaction("search google for python", "Search completed")
    
    # Store facts
    memory.store_fact("user_name", "Akshat")
    memory.store_fact("user_location", "India")
    
    # Get context
    context = memory.get_context()
    print("Context:")
    print(json.dumps(context, indent=2))
    
    # Get summary
    summary = memory.get_summary()
    print("\nSummary:")
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
