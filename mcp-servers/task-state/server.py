#!/usr/bin/env python3
"""
Task State Server - MCP Server for Agent Coordination and Instance Tracking

Provides centralized task tracking across Claude instances with persistent storage,
agent coordination, and instance state management.

This implementation uses the MCP stdio protocol directly for maximum compatibility.
"""

import json
import sqlite3
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/task-state-server.log'), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("task-state-server")

# Database path
DB_PATH = Path(__file__).parent / "tasks.db"

# Database connection pool
_db_connection = None


def get_db() -> sqlite3.Connection:
    """Get or create database connection."""
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False,
            isolation_level=None  # autocommit mode
        )
        _db_connection.row_factory = sqlite3.Row
        # Enable foreign key constraints
        _db_connection.execute("PRAGMA foreign_keys = ON")
        init_database(_db_connection)
    return _db_connection


def init_database(conn: sqlite3.Connection) -> None:
    """Initialize database schema."""
    cursor = conn.cursor()

    # Create tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            assignee TEXT,
            parent_task_id INTEGER,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (parent_task_id) REFERENCES tasks (id) ON DELETE CASCADE
        )
    """)

    # Create instance_states table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instance_states (
            instance_id TEXT PRIMARY KEY,
            current_task_id INTEGER,
            status TEXT DEFAULT 'active',
            working_directory TEXT,
            last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            FOREIGN KEY (current_task_id) REFERENCES tasks (id) ON DELETE SET NULL
        )
    """)

    # Create indices for common queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_instance_status ON instance_states(status)
    """)

    conn.commit()
    logger.info(f"Database initialized at {DB_PATH}")


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dictionary."""
    return {key: row[key] for key in row.keys()}


def serialize_metadata(metadata: Optional[dict]) -> Optional[str]:
    """Serialize metadata dict to JSON string."""
    if metadata is None:
        return None
    return json.dumps(metadata)


def deserialize_metadata(metadata_str: Optional[str]) -> Optional[dict]:
    """Deserialize JSON string to metadata dict."""
    if metadata_str is None or metadata_str == "":
        return None
    try:
        return json.loads(metadata_str)
    except json.JSONDecodeError:
        logger.error(f"Failed to deserialize metadata: {metadata_str}")
        return None


# Task Management Functions

def create_task(
    title: str,
    description: Optional[str] = None,
    status: str = "pending",
    priority: str = "medium",
    assignee: Optional[str] = None,
    parent_task_id: Optional[int] = None,
    metadata: Optional[dict] = None
) -> dict:
    """Create a new task."""
    # Validate status and priority
    valid_statuses = ["pending", "in_progress", "completed", "blocked"]
    valid_priorities = ["low", "medium", "high", "critical"]

    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    if priority not in valid_priorities:
        raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

    conn = get_db()
    cursor = conn.cursor()

    # Validate parent_task_id if provided
    if parent_task_id is not None:
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (parent_task_id,))
        if cursor.fetchone() is None:
            raise ValueError(f"Parent task {parent_task_id} does not exist")

    metadata_str = serialize_metadata(metadata)

    cursor.execute("""
        INSERT INTO tasks (title, description, status, priority, assignee, parent_task_id, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, description, status, priority, assignee, parent_task_id, metadata_str))

    task_id = cursor.lastrowid

    # Fetch the created task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    task = row_to_dict(row)
    task['metadata'] = deserialize_metadata(task['metadata'])

    logger.info(f"Created task {task_id}: {title}")
    return task


def update_task(task_id: int, updates: dict) -> dict:
    """Update task fields."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if task exists
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Task {task_id} not found")

    # Build update query
    allowed_fields = ["title", "description", "status", "priority", "assignee", "parent_task_id", "metadata"]
    update_fields = []
    update_values = []

    for field, value in updates.items():
        if field not in allowed_fields:
            raise ValueError(f"Invalid field: {field}")

        if field == "metadata" and isinstance(value, dict):
            value = serialize_metadata(value)

        update_fields.append(f"{field} = ?")
        update_values.append(value)

    if not update_fields:
        raise ValueError("No valid fields to update")

    # Always update updated_at
    update_fields.append("updated_at = CURRENT_TIMESTAMP")

    # Set completed_at if status changes to completed
    if "status" in updates and updates["status"] == "completed":
        update_fields.append("completed_at = CURRENT_TIMESTAMP")

    update_values.append(task_id)

    query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, update_values)

    # Fetch updated task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    task = row_to_dict(row)
    task['metadata'] = deserialize_metadata(task['metadata'])

    logger.info(f"Updated task {task_id}")
    return task


def delete_task(task_id: int) -> dict:
    """Delete a task."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if task exists and get it before deletion
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Task {task_id} not found")

    task = row_to_dict(row)
    task['metadata'] = deserialize_metadata(task['metadata'])

    # Delete task (CASCADE will handle subtasks)
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    logger.info(f"Deleted task {task_id}")
    return {"success": True, "deleted_task": task}


def get_task(task_id: int) -> dict:
    """Get a single task by ID."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    if row is None:
        raise ValueError(f"Task {task_id} not found")

    task = row_to_dict(row)
    task['metadata'] = deserialize_metadata(task['metadata'])

    # Get subtasks if any
    cursor.execute("SELECT id FROM tasks WHERE parent_task_id = ?", (task_id,))
    subtask_rows = cursor.fetchall()
    task['subtask_ids'] = [row['id'] for row in subtask_rows]

    return task


def query_tasks(filters: Optional[dict] = None) -> list:
    """Query tasks with optional filters."""
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM tasks"
    where_clauses = []
    params = []

    if filters:
        for field, value in filters.items():
            if field in ["status", "priority", "assignee", "parent_task_id"]:
                where_clauses.append(f"{field} = ?")
                params.append(value)
            elif field == "id":
                where_clauses.append("id = ?")
                params.append(value)
            elif field == "title_contains":
                where_clauses.append("title LIKE ?")
                params.append(f"%{value}%")
            elif field == "description_contains":
                where_clauses.append("description LIKE ?")
                params.append(f"%{value}%")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    tasks = []
    for row in rows:
        task = row_to_dict(row)
        task['metadata'] = deserialize_metadata(task['metadata'])
        tasks.append(task)

    logger.info(f"Queried tasks: found {len(tasks)} results")
    return tasks


# Instance State Management Functions

def get_instance_state(instance_id: str) -> dict:
    """Get state of a specific instance."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM instance_states WHERE instance_id = ?", (instance_id,))
    row = cursor.fetchone()

    if row is None:
        raise ValueError(f"Instance {instance_id} not found")

    state = row_to_dict(row)
    state['metadata'] = deserialize_metadata(state['metadata'])

    return state


def set_instance_state(instance_id: str, state: dict) -> dict:
    """Set or update instance state."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if instance exists
    cursor.execute("SELECT instance_id FROM instance_states WHERE instance_id = ?", (instance_id,))
    exists = cursor.fetchone() is not None

    # Extract allowed fields
    allowed_fields = ["current_task_id", "status", "working_directory", "metadata"]

    # Validate status if provided
    if "status" in state:
        valid_statuses = ["active", "idle", "busy"]
        if state["status"] not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    # Validate current_task_id if provided
    if state.get("current_task_id") is not None:
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (state["current_task_id"],))
        if cursor.fetchone() is None:
            raise ValueError(f"Task {state['current_task_id']} does not exist")

    if exists:
        # Update existing instance
        update_fields = []
        update_values = []

        for field, value in state.items():
            if field in allowed_fields:
                if field == "metadata" and isinstance(value, dict):
                    value = serialize_metadata(value)
                update_fields.append(f"{field} = ?")
                update_values.append(value)

        if update_fields:
            update_fields.append("last_heartbeat = CURRENT_TIMESTAMP")
            update_values.append(instance_id)

            query = f"UPDATE instance_states SET {', '.join(update_fields)} WHERE instance_id = ?"
            cursor.execute(query, update_values)
            logger.info(f"Updated instance state for {instance_id}")
    else:
        # Create new instance
        metadata_str = serialize_metadata(state.get("metadata"))
        cursor.execute("""
            INSERT INTO instance_states (instance_id, current_task_id, status, working_directory, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            instance_id,
            state.get("current_task_id"),
            state.get("status", "active"),
            state.get("working_directory"),
            metadata_str
        ))
        logger.info(f"Created instance state for {instance_id}")

    # Fetch and return the state
    return get_instance_state(instance_id)


def list_active_instances() -> list:
    """List all active instances."""
    conn = get_db()
    cursor = conn.cursor()

    # Consider instances active if heartbeat was within last 5 minutes
    cursor.execute("""
        SELECT * FROM instance_states
        WHERE datetime(last_heartbeat) > datetime('now', '-5 minutes')
        ORDER BY last_heartbeat DESC
    """)
    rows = cursor.fetchall()

    instances = []
    for row in rows:
        instance = row_to_dict(row)
        instance['metadata'] = deserialize_metadata(instance['metadata'])
        instances.append(instance)

    logger.info(f"Listed {len(instances)} active instances")
    return instances


def heartbeat(instance_id: str) -> dict:
    """Update instance heartbeat timestamp."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if instance exists
    cursor.execute("SELECT instance_id FROM instance_states WHERE instance_id = ?", (instance_id,))
    exists = cursor.fetchone() is not None

    if exists:
        cursor.execute("""
            UPDATE instance_states
            SET last_heartbeat = CURRENT_TIMESTAMP
            WHERE instance_id = ?
        """, (instance_id,))
        logger.debug(f"Heartbeat for instance {instance_id}")
    else:
        # Auto-create instance on first heartbeat
        cursor.execute("""
            INSERT INTO instance_states (instance_id, status)
            VALUES (?, 'active')
        """, (instance_id,))
        logger.info(f"Auto-created instance {instance_id} on heartbeat")

    return get_instance_state(instance_id)


# MCP Protocol Handler

def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool calls."""
    try:
        if name == "create_task":
            result = create_task(
                title=arguments["title"],
                description=arguments.get("description"),
                status=arguments.get("status", "pending"),
                priority=arguments.get("priority", "medium"),
                assignee=arguments.get("assignee"),
                parent_task_id=arguments.get("parent_task_id"),
                metadata=arguments.get("metadata")
            )
        elif name == "update_task":
            result = update_task(
                task_id=arguments["id"],
                updates=arguments["updates"]
            )
        elif name == "delete_task":
            result = delete_task(task_id=arguments["id"])
        elif name == "get_task":
            result = get_task(task_id=arguments["id"])
        elif name == "query_tasks":
            result = query_tasks(filters=arguments.get("filters"))
        elif name == "get_instance_state":
            result = get_instance_state(instance_id=arguments["instance_id"])
        elif name == "set_instance_state":
            result = set_instance_state(
                instance_id=arguments["instance_id"],
                state=arguments["state"]
            )
        elif name == "list_active_instances":
            result = list_active_instances()
        elif name == "heartbeat":
            result = heartbeat(instance_id=arguments["instance_id"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        return result

    except Exception as e:
        logger.error(f"Error executing {name}: {e}", exc_info=True)
        return {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get tool definitions for MCP."""
    return [
        {
            "name": "create_task",
            "description": "Create a new task with optional metadata",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title (required)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked"],
                        "description": "Task status (default: pending)"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Task priority (default: medium)"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Agent name or instance ID assigned to this task"
                    },
                    "parent_task_id": {
                        "type": "integer",
                        "description": "ID of parent task for subtasks"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Flexible JSON metadata for custom fields"
                    }
                },
                "required": ["title"]
            }
        },
        {
            "name": "update_task",
            "description": "Update one or more fields of an existing task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Task ID to update"
                    },
                    "updates": {
                        "type": "object",
                        "description": "Fields to update (title, description, status, priority, assignee, parent_task_id, metadata)"
                    }
                },
                "required": ["id", "updates"]
            }
        },
        {
            "name": "delete_task",
            "description": "Delete a task by ID (cascades to subtasks)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Task ID to delete"
                    }
                },
                "required": ["id"]
            }
        },
        {
            "name": "get_task",
            "description": "Get a single task by ID with subtask information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Task ID to retrieve"
                    }
                },
                "required": ["id"]
            }
        },
        {
            "name": "query_tasks",
            "description": "Query tasks with optional filters (status, priority, assignee, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Optional filters to apply"
                    }
                }
            }
        },
        {
            "name": "get_instance_state",
            "description": "Get state of a specific Claude instance",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "Instance ID to retrieve"
                    }
                },
                "required": ["instance_id"]
            }
        },
        {
            "name": "set_instance_state",
            "description": "Set or update instance state (current task, status, working directory, metadata)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "Instance ID to update"
                    },
                    "state": {
                        "type": "object",
                        "description": "State fields to set"
                    }
                },
                "required": ["instance_id", "state"]
            }
        },
        {
            "name": "list_active_instances",
            "description": "List all Claude instances with recent heartbeats (within last 5 minutes)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "heartbeat",
            "description": "Update instance heartbeat timestamp to mark as active",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "Instance ID sending heartbeat"
                    }
                },
                "required": ["instance_id"]
            }
        }
    ]


def send_message(message: Dict[str, Any]) -> None:
    """Send a message via stdio."""
    json_str = json.dumps(message)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()
    logger.debug(f"Sent: {json_str[:100]}...")


def read_message() -> Optional[Dict[str, Any]]:
    """Read a message from stdio."""
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        message = json.loads(line)
        logger.debug(f"Received: {json.dumps(message)[:100]}...")
        return message
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {e}")
        return None


def handle_initialize(request_id: Any, params: Dict[str, Any]) -> None:
    """Handle initialize request."""
    send_message({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "task-state-server",
                "version": "1.0.0"
            }
        }
    })


def handle_tools_list(request_id: Any) -> None:
    """Handle tools/list request."""
    send_message({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": get_tool_definitions()
        }
    })


def handle_tools_call(request_id: Any, params: Dict[str, Any]) -> None:
    """Handle tools/call request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    result = handle_tool_call(tool_name, arguments)

    send_message({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=str)
                }
            ]
        }
    })


def main():
    """Run the MCP server."""
    logger.info("Starting Task State Server...")

    # Initialize database on startup
    get_db()

    logger.info("Listening for MCP messages on stdin...")

    while True:
        message = read_message()
        if message is None:
            break

        if "method" not in message:
            logger.warning(f"Message missing method: {message}")
            continue

        method = message["method"]
        request_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            handle_initialize(request_id, params)
        elif method == "tools/list":
            handle_tools_list(request_id)
        elif method == "tools/call":
            handle_tools_call(request_id, params)
        else:
            logger.warning(f"Unknown method: {method}")
            if request_id is not None:
                send_message({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                })

    logger.info("Task State Server shutting down...")


if __name__ == "__main__":
    main()
