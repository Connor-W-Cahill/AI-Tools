# Quick Start Guide - Task State Server

Get up and running with the Task State MCP Server in 3 minutes.

## Installation

### 1. Verify Files

Check that these files exist:

```bash
ls -la /home/connor/.claude/mcp-servers/task-state/
```

You should see:
- `server.py` - Main server (executable)
- `test_server.py` - Test suite
- `README.md` - Full documentation
- `config-example.json` - Configuration template

### 2. Test the Server

Run the test suite to verify everything works:

```bash
cd /home/connor/.claude/mcp-servers/task-state
python3 test_server.py
```

You should see `✓ ALL TESTS PASSED` at the end.

### 3. Configure Claude Desktop

Add the server to your Claude Desktop configuration:

**Location:** `~/.config/claude/claude_desktop_config.json` (Linux) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

**Add this configuration:**

```json
{
  "mcpServers": {
    "task-state": {
      "command": "python3",
      "args": [
        "/home/connor/.claude/mcp-servers/task-state/server.py"
      ]
    }
  }
}
```

If you already have other servers configured, just add the `"task-state"` entry to the existing `mcpServers` object.

### 4. Restart Claude Desktop

Completely quit and restart Claude Desktop for the changes to take effect.

### 5. Verify Connection

In Claude, try this command:

```
List all available MCP tools
```

You should see 9 task-state tools:
- create_task
- update_task
- delete_task
- get_task
- query_tasks
- get_instance_state
- set_instance_state
- list_active_instances
- heartbeat

## First Commands

### Create Your First Task

```
Create a task titled "Test the task state server" with high priority
```

### View All Tasks

```
Query all tasks
```

### Update a Task

```
Update task 1 to status in_progress
```

### Mark Complete

```
Update task 1 to status completed
```

### Register Your Instance

```
Send a heartbeat for instance "my-claude-instance"
```

### View Active Instances

```
List all active instances
```

## Example Workflows

### Personal Todo List

```
Create task "Write project proposal" with priority high
Create task "Review pull requests" with priority medium
Create task "Update documentation" with priority low
Query tasks with filter status = pending
```

### Multi-Instance Coordination

```
# Instance 1
Send heartbeat for instance "builder-1"
Set instance state for "builder-1" with status busy and current_task_id 5

# Instance 2
Send heartbeat for instance "builder-2"
List active instances
Query tasks with filter status = pending and no assignee
```

### Project Management

```
# Create project structure
Create task "New Feature Development"
Create task "Design UI mockups" with parent_task_id 1
Create task "Implement backend API" with parent_task_id 1
Create task "Write tests" with parent_task_id 1

# Track progress
Get task 1
Query tasks with filter parent_task_id = 1
```

## Database Location

Your tasks are stored at:
```
/home/connor/.claude/mcp-servers/task-state/tasks.db
```

To backup:
```bash
cp /home/connor/.claude/mcp-servers/task-state/tasks.db ~/backups/tasks-$(date +%Y%m%d).db
```

## Logs

Server logs are written to:
```
/tmp/task-state-server.log
```

To view recent logs:
```bash
tail -f /tmp/task-state-server.log
```

## Troubleshooting

### Server not appearing in Claude

1. Check configuration file syntax is valid JSON
2. Verify the path in config matches: `/home/connor/.claude/mcp-servers/task-state/server.py`
3. Ensure server.py is executable: `chmod +x /home/connor/.claude/mcp-servers/task-state/server.py`
4. Restart Claude Desktop completely
5. Check logs in `/tmp/task-state-server.log`

### Database errors

If you see SQLite errors, reset the database:
```bash
rm /home/connor/.claude/mcp-servers/task-state/tasks.db
# Database will be recreated on next server start
```

### Permission errors

Ensure the server directory is writable:
```bash
chmod 755 /home/connor/.claude/mcp-servers/task-state
chmod 644 /home/connor/.claude/mcp-servers/task-state/server.py
```

## Next Steps

- Read the full [README.md](README.md) for detailed API documentation
- Explore advanced features like metadata and task hierarchy
- Set up automated heartbeats for instance tracking
- Integrate with your agent coordination workflows

## Support

For issues:
1. Check the [README.md](README.md) troubleshooting section
2. Review logs in `/tmp/task-state-server.log`
3. Run tests: `python3 test_server.py`
4. Verify database: `sqlite3 tasks.db ".schema"`

Happy task tracking!
