"""
Persistent cross-session memory for Jarvis.

Stores facts and conversation summaries in ~/.local/share/jarvis/memory.json.
Facts are user-specified preferences/context; summaries are auto-generated
at session end from the conversation history.
"""
import json
import os
import time

MEMORY_PATH = os.path.expanduser("~/.local/share/jarvis/memory.json")
MAX_SUMMARIES = 20
MAX_FACTS = 50


class JarvisMemory:
    def __init__(self):
        self._data = self._load()
        self._data["session_count"] = self._data.get("session_count", 0) + 1
        self._save()

    def _load(self):
        try:
            with open(MEMORY_PATH) as f:
                return json.load(f)
        except Exception:
            return {"facts": [], "summaries": [], "session_count": 0}

    def _save(self):
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        with open(MEMORY_PATH, "w") as f:
            json.dump(self._data, f, indent=2)

    def format_for_prompt(self):
        """Format memory content for inclusion in the system prompt."""
        parts = []

        facts = self._data.get("facts", [])
        if facts:
            parts.append("REMEMBERED FACTS:\n" + "\n".join(f"- {f}" for f in facts))

        summaries = self._data.get("summaries", [])
        if summaries:
            recent = summaries[-5:]
            parts.append("RECENT SESSIONS:\n" + "\n".join(
                "- [{}] {}".format(s["date"], s["summary"]) for s in recent
            ))

        return "\n\n".join(parts) if parts else ""

    def add_fact(self, fact):
        """Add a fact to persistent memory. Deduplicates."""
        facts = self._data.setdefault("facts", [])
        if fact not in facts:
            facts.append(fact)
            if len(facts) > MAX_FACTS:
                facts.pop(0)
            self._save()
            print("[Memory] Fact saved: {}".format(fact[:60]), flush=True)

    def add_session_summary(self, summary):
        """Save a summary of the completed conversation."""
        summaries = self._data.setdefault("summaries", [])
        summaries.append({
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "summary": summary[:500],
        })
        if len(summaries) > MAX_SUMMARIES:
            summaries.pop(0)
        self._save()

    def remove_fact(self, keyword):
        """Remove facts matching a keyword. Returns count removed."""
        facts = self._data.get("facts", [])
        before = len(facts)
        self._data["facts"] = [f for f in facts if keyword.lower() not in f.lower()]
        removed = before - len(self._data["facts"])
        if removed:
            self._save()
        return removed

    @property
    def session_count(self):
        return self._data.get("session_count", 1)

    @property
    def facts(self):
        return list(self._data.get("facts", []))
