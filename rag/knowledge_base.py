"""
RAG Knowledge Base — persistent, searchable memory for the AI workflow.

Indexes:
- Beads issues (task history, decisions, close reasons)
- aio-context entries (decisions, patterns, learnings, warnings, handoffs)
- Conversation summaries (saved after each session)
- Project docs (CLAUDE.md, agent definitions, README)

Uses ChromaDB for vector storage with local embeddings (Ollama nomic-embed-text
if available, otherwise falls back to ChromaDB default).
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ChromaDB needs SQLite >= 3.35; Python 3.8 ships 3.31.
# pysqlite3-binary provides a newer version.
try:
    import pysqlite3
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import chromadb
from chromadb.config import Settings

# ── Config ──────────────────────────────────────────────────────────────

AI_TOOLS_DIR = Path(__file__).resolve().parent.parent
DB_DIR = Path.home() / ".local" / "share" / "ai-knowledge"
BEADS_JSONL = AI_TOOLS_DIR / ".beads" / "issues.jsonl"
CONTEXT_FILE = Path.home() / ".ai-orchestrator" / "state.json"
AGENTS_DIR = AI_TOOLS_DIR / "agents"
DOCS_DIR = AI_TOOLS_DIR / "docs"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-connor-AI-Tools" / "memory"

# Collections
COLL_TASKS = "beads_tasks"
COLL_CONTEXT = "aio_context"
COLL_CONVERSATIONS = "conversations"
COLL_DOCS = "project_docs"


class KnowledgeBase:
    """Persistent RAG knowledge base backed by ChromaDB."""

    def __init__(self, db_dir: Optional[str] = None):
        db_path = db_dir or str(DB_DIR)
        os.makedirs(db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collections
        self.tasks = self.client.get_or_create_collection(
            name=COLL_TASKS,
            metadata={"description": "Beads task history"},
        )
        self.context = self.client.get_or_create_collection(
            name=COLL_CONTEXT,
            metadata={"description": "aio-context shared knowledge"},
        )
        self.conversations = self.client.get_or_create_collection(
            name=COLL_CONVERSATIONS,
            metadata={"description": "Conversation summaries"},
        )
        self.docs = self.client.get_or_create_collection(
            name=COLL_DOCS,
            metadata={"description": "Project documentation"},
        )

    # ── Indexing ────────────────────────────────────────────────────────

    def index_beads(self, jsonl_path: Optional[str] = None):
        """Index all beads issues from the JSONL file."""
        path = Path(jsonl_path) if jsonl_path else BEADS_JSONL
        if not path.exists():
            print(f"[KB] Beads file not found: {path}")
            return 0

        count = 0
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    issue = json.loads(line)
                except json.JSONDecodeError:
                    continue

                issue_id = issue.get("id", "")
                title = issue.get("title", "")
                desc = issue.get("description", "")
                notes = issue.get("notes", "")
                status = issue.get("status", "")
                close_reason = issue.get("close_reason", "")
                issue_type = issue.get("issue_type", "")
                priority = issue.get("priority", "")

                # Build searchable document
                parts = [f"[{issue_type}] {title}"]
                if desc:
                    parts.append(f"Description: {desc}")
                if notes:
                    parts.append(f"Notes: {notes}")
                if close_reason:
                    parts.append(f"Resolution: {close_reason}")

                # Include comments
                for comment in issue.get("comments", []):
                    parts.append(f"Comment: {comment.get('text', '')}")

                document = "\n".join(parts)

                self.tasks.upsert(
                    ids=[issue_id],
                    documents=[document],
                    metadatas=[{
                        "title": title,
                        "status": status,
                        "type": issue_type,
                        "priority": str(priority),
                        "created_at": issue.get("created_at", ""),
                        "closed_at": issue.get("closed_at", ""),
                    }],
                )
                count += 1

        print(f"[KB] Indexed {count} beads issues")
        return count

    def index_aio_context(self, state_path: Optional[str] = None):
        """Index aio-context entries from the orchestrator state file."""
        path = Path(state_path) if state_path else CONTEXT_FILE
        if not path.exists():
            print(f"[KB] State file not found: {path}")
            return 0

        try:
            with open(path) as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"[KB] Could not read state file: {path}")
            return 0

        count = 0
        for entry in state.get("context", []):
            entry_id = entry.get("id", f"ctx-{count}")
            category = entry.get("category", "unknown")
            message = entry.get("message", "")
            author = entry.get("author", "")
            timestamp = entry.get("timestamp", "")

            document = f"[{category}] {message}"
            if author:
                document += f" (by {author})"

            self.context.upsert(
                ids=[entry_id],
                documents=[document],
                metadatas=[{
                    "category": category,
                    "author": author,
                    "timestamp": timestamp,
                }],
            )
            count += 1

        print(f"[KB] Indexed {count} context entries")
        return count

    def index_docs(self):
        """Index project documentation (CLAUDE.md, agents, README, MEMORY.md)."""
        count = 0
        files_to_index = []

        # Main project docs
        for name in ["CLAUDE.md", "GEMINI.md", "README.md"]:
            p = AI_TOOLS_DIR / name
            if p.exists():
                files_to_index.append(("project", str(p)))

        # Agent definitions
        if AGENTS_DIR.exists():
            for f in AGENTS_DIR.glob("*.md"):
                files_to_index.append(("agent", str(f)))

        # Docs directory
        if DOCS_DIR.exists():
            for f in DOCS_DIR.glob("*.md"):
                files_to_index.append(("docs", str(f)))

        # Memory files
        if MEMORY_DIR.exists():
            for f in MEMORY_DIR.glob("*.md"):
                files_to_index.append(("memory", str(f)))

        for doc_type, filepath in files_to_index:
            try:
                with open(filepath) as f:
                    content = f.read()
            except IOError:
                continue

            # Chunk large docs by section (## headers)
            chunks = self._chunk_by_headers(content)
            basename = os.path.basename(filepath)

            for i, chunk in enumerate(chunks):
                doc_id = f"doc-{basename}-{i}"
                self.docs.upsert(
                    ids=[doc_id],
                    documents=[chunk],
                    metadatas=[{
                        "file": basename,
                        "type": doc_type,
                        "chunk": str(i),
                    }],
                )
                count += 1

        print(f"[KB] Indexed {count} doc chunks")
        return count

    def _chunk_by_headers(self, text: str, max_chunk: int = 1000) -> list:
        """Split markdown by ## headers. Merge small sections."""
        sections = re.split(r'\n(?=## )', text)
        chunks = []
        current = ""

        for section in sections:
            if len(current) + len(section) > max_chunk and current:
                chunks.append(current.strip())
                current = section
            else:
                current += "\n" + section if current else section

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text]

    # ── Saving new knowledge ────────────────────────────────────────────

    def save_conversation(self, summary: str, session_id: str = ""):
        """Save a conversation summary for future retrieval."""
        if not session_id:
            session_id = f"conv-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self.conversations.upsert(
            ids=[session_id],
            documents=[summary],
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                "type": "conversation",
            }],
        )

    # ── Retrieval ───────────────────────────────────────────────────────

    def search(self, query: str, n_results: int = 5, collections: Optional[list] = None) -> list:
        """Search across all or specified collections.

        Returns list of {document, metadata, collection, distance}.
        """
        targets = collections or [COLL_TASKS, COLL_CONTEXT, COLL_CONVERSATIONS, COLL_DOCS]
        results = []

        for coll_name in targets:
            try:
                coll = self.client.get_collection(coll_name)
                if coll.count() == 0:
                    continue
                hits = coll.query(
                    query_texts=[query],
                    n_results=min(n_results, coll.count()),
                )
                for i in range(len(hits["ids"][0])):
                    results.append({
                        "id": hits["ids"][0][i],
                        "document": hits["documents"][0][i],
                        "metadata": hits["metadatas"][0][i] if hits["metadatas"] else {},
                        "collection": coll_name,
                        "distance": hits["distances"][0][i] if hits["distances"] else None,
                    })
            except Exception as e:
                print(f"[KB] Error searching {coll_name}: {e}")

        # Sort by distance (lower = better match)
        results.sort(key=lambda r: r.get("distance", float("inf")))
        return results[:n_results]

    def search_tasks(self, query: str, n_results: int = 5, status: Optional[str] = None) -> list:
        """Search beads tasks, optionally filtering by status."""
        where = {"status": status} if status else None
        try:
            hits = self.tasks.query(
                query_texts=[query],
                n_results=min(n_results, max(1, self.tasks.count())),
                where=where,
            )
            return [{
                "id": hits["ids"][0][i],
                "document": hits["documents"][0][i],
                "metadata": hits["metadatas"][0][i],
                "distance": hits["distances"][0][i],
            } for i in range(len(hits["ids"][0]))]
        except Exception as e:
            print(f"[KB] Error searching tasks: {e}")
            return []

    # ── Full reindex ────────────────────────────────────────────────────

    def reindex_all(self):
        """Reindex everything from source files."""
        print("[KB] Starting full reindex...")
        self.index_beads()
        self.index_aio_context()
        self.index_docs()
        print("[KB] Reindex complete.")

    # ── Stats ───────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return collection sizes."""
        return {
            "tasks": self.tasks.count(),
            "context": self.context.count(),
            "conversations": self.conversations.count(),
            "docs": self.docs.count(),
        }


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    import sys

    kb = KnowledgeBase()

    if len(sys.argv) < 2:
        print("Usage: knowledge_base.py [reindex|search <query>|stats]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "reindex":
        kb.reindex_all()
        print(f"Stats: {kb.stats()}")

    elif cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = kb.search(query)
        for r in results:
            print(f"\n--- [{r['collection']}] {r['id']} (dist={r['distance']:.3f}) ---")
            print(r["document"][:300])

    elif cmd == "stats":
        print(kb.stats())

    else:
        print("Usage: knowledge_base.py [reindex|search <query>|stats]")


if __name__ == "__main__":
    main()
