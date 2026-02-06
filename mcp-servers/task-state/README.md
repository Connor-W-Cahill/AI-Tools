# Task State Server - MCP Server

Centralized task tracking and agent coordination system for Claude instances. Provides persistent task management, instance state tracking, and coordination capabilities across multiple agent sessions.

## Features

- **Task Management**: Full CRUD operations for tasks with hierarchical support
- **Instance Tracking**: Monitor and coordinate multiple Claude instances
- **Persistent Storage**: SQLite database for cross-session persistence
- **Flexible Metadata**: JSON metadata fields for custom data
- **Task Hierarchy**: Support for parent-child task relationships
- **Query & Filter**: Powerful query capabilities with multiple filters
- **Heartbeat System**: Automatic instance liveness tracking

## Installation

1. Install dependencies:
```bash
cd /home/connor/.claude/mcp-servers/task-state
pip install -r requirements.txt
```

2. Make the server executable:
```bash
chmod +x server.py
```

3. Configure in Claude Desktop (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "task-state": {
      "command": "python3",
      "args": ["/home/connor/.claude/mcp-servers/task-state/server.py"]
    }
  }
}
```

Or for Claude CLI, add to your MCP configuration.

## Database Schema

### Tasks Table
- `id`: Primary key
- `title`: Task title (required)
- `description`: Detailed description
- `status`: pending | in_progress | completed | blocked
- `priority`: low | medium | high | critical
- `assignee`: Agent name or instance ID
- `parent_task_id`: For subtasks/hierarchy
- `metadata`: JSON for custom fields
- `created_at`, `updated_at`, `completed_at`: Timestamps

### Instance States Table
- `instance_id`: Primary key
- `current_task_id`: Active task reference
- `status`: active | idle | busy
- `working_directory`: Current working directory
- `last_heartbeat`: Last activity timestamp
- `metadata`: JSON for custom fields

## MCP Tools

### Task Management

#### create_task
Create a new task.

**Parameters:**
- `title` (required): Task title
- `description`: Detailed description
- `status`: pending | in_progress | completed | blocked (default: pending)
- `priority`: low | medium | high | critical (default: medium)
- `assignee`: Agent/instance assigned to task
- `parent_task_id`: Parent task ID for subtasks
- `metadata`: Custom JSON metadata

**Example:**
```json
{
  "title": "Implement user authentication",
  "description": "Add JWT-based auth to API",
  "status": "in_progress",
  "priority": "high",
  "assignee": "claude-instance-1",
  "metadata": {
    "project": "api-v2",
    "tags": ["security", "backend"]
  }
}
```

#### update_task
Update existing task fields.

**Parameters:**
- `id` (required): Task ID
- `updates` (required): Object with fields to update

**Example:**
```json
{
  "id": 1,
  "updates": {
    "status": "completed",
    "metadata": {
      "completion_notes": "All tests passing"
    }
  }
}
```

#### delete_task
Delete a task (cascades to subtasks).

**Parameters:**
- `id` (required): Task ID

#### get_task
Retrieve a single task by ID.

**Parameters:**
- `id` (required): Task ID

**Returns:** Task object with `subtask_ids` array

#### query_tasks
Query tasks with optional filters.

**Parameters:**
- `filters`: Optional object with:
  - `status`: Filter by status
  - `priority`: Filter by priority
  - `assignee`: Filter by assignee
  - `parent_task_id`: Filter by parent
  - `id`: Get specific task
  - `title_contains`: Search in title
  - `description_contains`: Search in description

**Example:**
```json
{
  "filters": {
    "status": "in_progress",
    "assignee": "claude-instance-1"
  }
}
```

### Instance Management

#### get_instance_state
Get state of a specific instance.

**Parameters:**
- `instance_id` (required): Instance identifier

#### set_instance_state
Create or update instance state.

**Parameters:**
- `instance_id` (required): Instance identifier
- `state` (required): Object with:
  - `current_task_id`: Active task ID
  - `status`: active | idle | busy
  - `working_directory`: Current working directory
  - `metadata`: Custom JSON metadata

**Example:**
```json
{
  "instance_id": "claude-instance-1",
  "state": {
    "current_task_id": 5,
    "status": "busy",
    "working_directory": "/home/user/project",
    "metadata": {
      "session_start": "2026-01-21T10:00:00Z",
      "capabilities": ["coding", "analysis"]
    }
  }
}
```

#### list_active_instances
List all instances with heartbeats within last 5 minutes.

**Parameters:** None

#### heartbeat
Update instance heartbeat timestamp.

**Parameters:**
- `instance_id` (required): Instance identifier

**Note:** Auto-creates instance on first heartbeat.

## Usage Examples

### Basic Task Workflow

1. **Create a task:**
```
Create a task titled "Review pull request #123" with high priority
```

2. **Assign to instance:**
```
Update task 1 to assign it to instance "reviewer-agent"
```

3. **Track progress:**
```
Update task 1 status to in_progress
```

4. **Complete task:**
```
Update task 1 status to completed
```

### Hierarchical Tasks

1. **Create parent task:**
```
Create a task "Build authentication system"
```

2. **Create subtasks:**
```
Create a task "Implement JWT tokens" with parent_task_id 1
Create a task "Add password hashing" with parent_task_id 1
Create a task "Create login endpoint" with parent_task_id 1
```

3. **Query all subtasks:**
```
Query tasks with filter parent_task_id = 1
```

### Multi-Instance Coordination

1. **Register instance:**
```
Send heartbeat for instance "builder-1"
```

2. **Claim a task:**
```
Set instance state for "builder-1" with current_task_id 5 and status busy
```

3. **Check active instances:**
```
List active instances
```

4. **Find available work:**
```
Query tasks with filter status = pending
```

### Advanced Queries

**Find blocked tasks:**
```
Query tasks with filter status = blocked
```

**Find critical priority tasks:**
```
Query tasks with filter priority = critical
```

**Search by keyword:**
```
Query tasks with filter title_contains = "authentication"
```

**Get all tasks for an assignee:**
```
Query tasks with filter assignee = "claude-instance-1"
```

## Database Location

Database file: `/home/connor/.claude/mcp-servers/task-state/tasks.db`

The database is automatically created on first run with proper schema and indices.

## Best Practices

### For Task Management
- Use descriptive titles and detailed descriptions
- Set appropriate priority levels
- Update status regularly as work progresses
- Use metadata for custom fields (tags, links, notes)
- Leverage task hierarchy for complex projects

### For Instance Coordination
- Send regular heartbeats (every 1-2 minutes)
- Update instance state when starting/completing tasks
- Use metadata for instance capabilities and session info
- Query active instances before claiming new work
- Set status to 'idle' when waiting for work

### For Agent Systems
- Create tasks for each major workflow step
- Use parent_task_id to track subtask relationships
- Store workflow context in metadata
- Query pending tasks to distribute work
- Update task status atomically

## Error Handling

All tools return structured error messages:
```json
{
  "error": "Task 999 not found",
  "tool": "get_task",
  "arguments": {"id": 999}
}
```

Common errors:
- Task/instance not found
- Invalid status/priority values
- Invalid parent_task_id reference
- Missing required fields

## Maintenance

### Backup Database
```bash
cp /home/connor/.claude/mcp-servers/task-state/tasks.db /path/to/backup/
```

### Clear Old Instances
```sql
DELETE FROM instance_states
WHERE datetime(last_heartbeat) < datetime('now', '-1 day');
```

### Archive Completed Tasks
```sql
-- Create archive table
CREATE TABLE tasks_archive AS SELECT * FROM tasks WHERE 1=0;

-- Move completed tasks older than 30 days
INSERT INTO tasks_archive
SELECT * FROM tasks
WHERE status = 'completed'
  AND datetime(completed_at) < datetime('now', '-30 days');

DELETE FROM tasks
WHERE status = 'completed'
  AND datetime(completed_at) < datetime('now', '-30 days');
```

## Architecture Notes

- **Thread Safety**: Uses SQLite's autocommit mode for safety
- **Cascading Deletes**: Deleting parent tasks removes all subtasks
- **Automatic Timestamps**: created_at, updated_at, completed_at managed automatically
- **Heartbeat TTL**: Instances considered active if heartbeat within 5 minutes
- **Indices**: Optimized for common queries (status, assignee, parent_task_id)

## Troubleshooting

### Server won't start
- Check Python version (3.8+ required)
- Verify mcp package is installed: `pip show mcp`
- Check file permissions on server.py

### Database locked errors
- Ensure only one server instance is running
- Check file permissions on tasks.db
- Verify no other process has the database open

### Missing data
- Check database file exists: `ls -la /home/connor/.claude/mcp-servers/task-state/tasks.db`
- Verify table schema: `sqlite3 tasks.db ".schema"`

## License

MIT License - Free for personal and commercial use.

## Support

For issues or questions about the MCP protocol, see:
- MCP Documentation: https://modelcontextprotocol.io
- MCP Specification: https://spec.modelcontextprotocol.io
