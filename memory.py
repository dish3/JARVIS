#!/usr/bin/env python3
"""
JARVIS Memory - Persistent Storage
Stores interactions and user facts in memory.json.
In-memory cache keeps reads fast; disk write happens after every mutation.
All existing method signatures are preserved exactly.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger('MEMORY')

# memory.json lives next to this file so it works regardless of cwd
_MEMORY_FILE = Path(__file__).parent / 'memory.json'
_MAX_INTERACTIONS = 500


class Memory:
    """Persistent storage for interactions and context.

    Public API (unchanged):
        store_interaction(goal, result)
        store_fact(key, value)
        get_fact(key) -> value | None
        get_context() -> dict
        get_summary() -> dict
        clear()
    """

    def __init__(self):
        logger.info("Initializing Memory...")

        self.session_start = datetime.now()

        # In-memory cache — populated from disk on startup
        self.interactions: List[Dict] = []
        self.user_facts: Dict[str, Any] = {}

        # Load persisted data (safe — corrupted JSON is handled gracefully)
        self._load()

        logger.info(
            f"[OK] Memory initialized "
            f"({len(self.interactions)} interactions, "
            f"{len(self.user_facts)} facts loaded from disk)"
        )

    # ── Public API (signatures unchanged) ─────────────────────────────────────

    def store_interaction(self, goal: str, result: Any) -> None:
        """Store a goal-result interaction and persist to disk."""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'goal': goal,
            'result': result,
        }

        self.interactions.append(interaction)
        logger.info(f"[MEMORY] Stored interaction #{len(self.interactions)}")

        # Keep only the most recent N interactions in memory and on disk
        if len(self.interactions) > _MAX_INTERACTIONS:
            self.interactions = self.interactions[-_MAX_INTERACTIONS:]

        # Auto-save after every interaction
        self._save()

    def store_fact(self, key: str, value: Any) -> None:
        """Store a user fact and persist to disk."""
        self.user_facts[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
        }
        logger.info(f"[MEMORY] Stored fact: {key} = {value}")

        # Auto-save after every fact update
        self._save()

    def get_fact(self, key: str) -> Optional[Any]:
        """Retrieve a user fact from the in-memory cache."""
        if key in self.user_facts:
            return self.user_facts[key]['value']
        return None

    def get_context(self) -> Dict[str, Any]:
        """Get current context for the planner.
        
        Returns last 10 full interactions plus a compressed summary
        of older interactions to give the LLM rich context without
        token bloat.
        """
        recent_interactions = self.interactions[-10:] if self.interactions else []
        older_summary = self._summarize_old_interactions()

        return {
            'session_duration': str(datetime.now() - self.session_start),
            'total_interactions': len(self.interactions),
            'recent_interactions': recent_interactions,
            'older_summary': older_summary,
            'user_facts': self.user_facts,
        }

    def _summarize_old_interactions(self) -> str:
        """Compress interactions older than the last 10 into a brief summary.
        
        This keeps the context window manageable while preserving
        historical awareness for the Planner.
        """
        if len(self.interactions) <= 10:
            return ""
        
        older = self.interactions[:-10]
        
        # Build a compressed summary: just goals and whether they succeeded
        summary_parts = []
        for interaction in older[-20:]:  # Summarize at most 20 older ones
            goal = interaction.get('goal', 'unknown')
            result = interaction.get('result', '')
            # Truncate result to first 50 chars
            result_preview = str(result)[:50] if result else 'no result'
            summary_parts.append(f"- {goal} → {result_preview}")
        
        prefix = f"({len(older)} older interactions"
        if len(older) > 20:
            prefix += f", showing last 20"
        prefix += "):\n"
        
        return prefix + "\n".join(summary_parts)

    def get_summary(self) -> Dict[str, Any]:
        """Get memory summary."""
        return {
            'session_start': self.session_start.isoformat(),
            'total_interactions': len(self.interactions),
            'user_facts_count': len(self.user_facts),
            'memory_size_kb': round(len(json.dumps(self.interactions)) / 1024, 2),
            'memory_file': str(_MEMORY_FILE),
        }

    def clear(self) -> None:
        """Clear all memory (in-memory and on disk)."""
        logger.warning("[MEMORY] Clearing all memory")
        self.interactions = []
        self.user_facts = {}
        self.session_start = datetime.now()
        self._save()

    # ── Persistence (private) ──────────────────────────────────────────────────

    def _load(self) -> None:
        """
        Load interactions and facts from memory.json into the in-memory cache.
        Handles three failure cases safely:
          1. File does not exist  → start fresh, no error
          2. File is empty        → start fresh, no error
          3. File is corrupt JSON → rename to memory.json.bak, start fresh
        """
        if not _MEMORY_FILE.exists():
            logger.info("[MEMORY] No memory.json found — starting fresh")
            return

        try:
            raw = _MEMORY_FILE.read_text(encoding='utf-8').strip()
            if not raw:
                logger.info("[MEMORY] memory.json is empty — starting fresh")
                return

            data = json.loads(raw)

            # Validate expected structure
            if not isinstance(data, dict):
                raise ValueError("Root is not a JSON object")

            self.interactions = data.get('interactions', [])
            self.user_facts   = data.get('user_facts', {})

            # Enforce type safety — discard if wrong type
            if not isinstance(self.interactions, list):
                logger.warning("[MEMORY] interactions field is not a list — resetting")
                self.interactions = []
            if not isinstance(self.user_facts, dict):
                logger.warning("[MEMORY] user_facts field is not a dict — resetting")
                self.user_facts = {}

            # Trim to max on load (in case limit was lower in a previous version)
            if len(self.interactions) > _MAX_INTERACTIONS:
                self.interactions = self.interactions[-_MAX_INTERACTIONS:]

            logger.info(
                f"[MEMORY] Loaded {len(self.interactions)} interactions "
                f"and {len(self.user_facts)} facts from {_MEMORY_FILE}"
            )

        except (json.JSONDecodeError, ValueError) as e:
            # Corrupt file — back it up and start fresh
            backup = _MEMORY_FILE.with_suffix('.json.bak')
            try:
                shutil.copy2(_MEMORY_FILE, backup)
                logger.warning(
                    f"[MEMORY] Corrupt memory.json ({e}) — "
                    f"backed up to {backup.name}, starting fresh"
                )
            except Exception as backup_err:
                logger.warning(f"[MEMORY] Could not back up corrupt file: {backup_err}")

            self.interactions = []
            self.user_facts   = {}

        except Exception as e:
            # Any other unexpected error — log and start fresh, never crash
            logger.error(f"[MEMORY] Unexpected load error: {e} — starting fresh")
            self.interactions = []
            self.user_facts   = {}

    def _save(self) -> None:
        """
        Write current state to memory.json atomically.
        Uses a temp file + rename so a crash mid-write never corrupts the file.
        """
        data = {
            'saved_at':     datetime.now().isoformat(),
            'interactions': self.interactions,
            'user_facts':   self.user_facts,
        }

        # Write to a temp file first, then rename — atomic on all platforms
        tmp = _MEMORY_FILE.with_suffix('.json.tmp')
        try:
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            # os.replace is atomic on POSIX; on Windows it overwrites atomically
            os.replace(tmp, _MEMORY_FILE)
            logger.debug(f"[MEMORY] Saved to {_MEMORY_FILE}")

        except Exception as e:
            logger.error(f"[MEMORY] Save failed: {e}")
            # Clean up temp file if it exists
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass


def main():
    """Test memory persistence"""
    import tempfile, sys

    # Use a temp file so the test doesn't pollute the real memory.json
    global _MEMORY_FILE
    _MEMORY_FILE = Path(tempfile.mktemp(suffix='.json'))

    print(f"Test memory file: {_MEMORY_FILE}")

    # ── Round 1: write ────────────────────────────────────────────────────────
    m1 = Memory()
    m1.store_interaction("open chrome", "Chrome opened successfully")
    m1.store_interaction("search google for python", "Search completed")
    m1.store_fact("user_name", "Disha")
    m1.store_fact("user_location", "India")

    print("\n[Round 1] Summary:")
    print(json.dumps(m1.get_summary(), indent=2))

    # ── Round 2: reload — should see persisted data ───────────────────────────
    m2 = Memory()
    print("\n[Round 2] Loaded from disk:")
    print(f"  interactions: {len(m2.interactions)}")
    print(f"  user_name:    {m2.get_fact('user_name')}")
    print(f"  user_location:{m2.get_fact('user_location')}")
    assert len(m2.interactions) == 2, "Expected 2 interactions"
    assert m2.get_fact('user_name') == 'Disha', "Expected user_name = Disha"

    # ── Round 3: corrupt file handling ───────────────────────────────────────
    _MEMORY_FILE.write_text("{ this is not valid json !!!", encoding='utf-8')
    m3 = Memory()
    print(f"\n[Round 3] After corrupt file: interactions={len(m3.interactions)} (expected 0)")
    assert len(m3.interactions) == 0, "Expected 0 after corrupt file"
    backup = _MEMORY_FILE.with_suffix('.json.bak')
    assert backup.exists(), "Expected backup file to exist"
    print(f"  Backup created: {backup.name}")

    # ── Round 4: clear ────────────────────────────────────────────────────────
    m3.store_interaction("test", "result")
    m3.clear()
    m4 = Memory()
    print(f"\n[Round 4] After clear: interactions={len(m4.interactions)} (expected 0)")
    assert len(m4.interactions) == 0, "Expected 0 after clear"

    # Cleanup
    for f in [_MEMORY_FILE, backup, _MEMORY_FILE.with_suffix('.json.tmp')]:
        try: f.unlink()
        except: pass

    print("\n[OK] All tests passed")


if __name__ == '__main__':
    main()
