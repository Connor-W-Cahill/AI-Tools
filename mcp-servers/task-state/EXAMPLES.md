# Task State Server - Usage Examples

Practical examples for common use cases.

## Table of Contents

1. [Personal Task Management](#personal-task-management)
2. [Multi-Agent Coordination](#multi-agent-coordination)
3. [Project Workflows](#project-workflows)
4. [Instance Monitoring](#instance-monitoring)
5. [Advanced Queries](#advanced-queries)

## Personal Task Management

### Daily Todo List

```python
# Morning: Create tasks for the day
create_task(
    title="Review code changes from yesterday",
    priority="high",
    metadata={"category": "code-review", "estimate": "30min"}
)

create_task(
    title="Update API documentation",
    priority="medium",
    metadata={"category": "documentation", "estimate": "1h"}
)

create_task(
    title="Research new testing framework",
    priority="low",
    metadata={"category": "research", "estimate": "2h"}
)

# View all pending work
query_tasks(filters={"status": "pending"})

# Start working
update_task(id=1, updates={"status": "in_progress"})

# Complete task
update_task(id=1, updates={"status": "completed"})

# End of day: View what's left
query_tasks(filters={"status": "in_progress"})
```

### Project Task List

```python
# Create main project task
project = create_task(
    title="Build User Authentication System",
    description="Implement JWT-based authentication with refresh tokens",
    priority="critical",
    metadata={
        "project": "api-v2",
        "deadline": "2026-02-01",
        "team": "backend"
    }
)

# Break into subtasks
create_task(
    title="Design database schema for users",
    parent_task_id=project["id"],
    priority="high",
    metadata={"estimate": "2h"}
)

create_task(
    title="Implement JWT token generation",
    parent_task_id=project["id"],
    priority="high",
    metadata={"estimate": "3h"}
)

create_task(
    title="Create login/logout endpoints",
    parent_task_id=project["id"],
    priority="high",
    metadata={"estimate": "4h"}
)

create_task(
    title="Add password hashing with bcrypt",
    parent_task_id=project["id"],
    priority="high",
    metadata={"estimate": "2h"}
)

create_task(
    title="Write integration tests",
    parent_task_id=project["id"],
    priority="medium",
    metadata={"estimate": "3h"}
)

# View project progress
task = get_task(project["id"])
print(f"Project: {task['title']}")
print(f"Subtasks: {task['subtask_ids']}")

# Get all subtasks
subtasks = query_tasks(filters={"parent_task_id": project["id"]})
```

## Multi-Agent Coordination

### Work Distribution

```python
# Agent Coordinator: Create work queue
tasks = [
    {"title": "Process dataset A", "priority": "high"},
    {"title": "Process dataset B", "priority": "high"},
    {"title": "Process dataset C", "priority": "medium"},
    {"title": "Process dataset D", "priority": "medium"},
]

task_ids = []
for task_data in tasks:
    task = create_task(**task_data)
    task_ids.append(task["id"])

# Worker Agent 1: Register and claim work
heartbeat(instance_id="worker-1")
set_instance_state(
    instance_id="worker-1",
    state={
        "status": "active",
        "working_directory": "/workspace/worker-1",
        "metadata": {"capabilities": ["data-processing"]}
    }
)

# Find available work
available = query_tasks(filters={
    "status": "pending",
    "priority": "high"
})

if available:
    task = available[0]
    # Claim the task
    update_task(
        id=task["id"],
        updates={"status": "in_progress", "assignee": "worker-1"}
    )

    # Update instance state
    set_instance_state(
        instance_id="worker-1",
        state={
            "status": "busy",
            "current_task_id": task["id"]
        }
    )

# Worker Agent 2: Same process
heartbeat(instance_id="worker-2")
# ... claim different task

# Coordinator: Monitor progress
active_instances = list_active_instances()
print(f"Active workers: {len(active_instances)}")

in_progress = query_tasks(filters={"status": "in_progress"})
print(f"Tasks in progress: {len(in_progress)}")

pending = query_tasks(filters={"status": "pending"})
print(f"Tasks waiting: {len(pending)}")
```

### Load Balancing

```python
# Monitor instance workload
instances = list_active_instances()

for instance in instances:
    instance_id = instance["instance_id"]

    # Get tasks assigned to this instance
    assigned_tasks = query_tasks(filters={
        "assignee": instance_id,
        "status": "in_progress"
    })

    print(f"{instance_id}: {len(assigned_tasks)} active tasks")

    # If instance is idle, assign work
    if len(assigned_tasks) == 0:
        pending = query_tasks(filters={"status": "pending"})
        if pending:
            task = pending[0]
            update_task(
                id=task["id"],
                updates={"assignee": instance_id, "status": "in_progress"}
            )
```

## Project Workflows

### Sprint Planning

```python
# Create sprint
sprint = create_task(
    title="Sprint 15 - API Improvements",
    description="Focus on performance and reliability",
    metadata={
        "sprint_number": 15,
        "start_date": "2026-01-20",
        "end_date": "2026-02-03",
        "story_points": 0
    }
)

# Add user stories
stories = [
    {
        "title": "Implement API caching",
        "description": "Add Redis caching to reduce database load",
        "priority": "high",
        "metadata": {"story_points": 5, "type": "feature"}
    },
    {
        "title": "Fix memory leak in worker process",
        "description": "Investigate and fix memory leak reported in production",
        "priority": "critical",
        "metadata": {"story_points": 3, "type": "bug"}
    },
    {
        "title": "Add rate limiting",
        "description": "Implement per-user rate limiting",
        "priority": "high",
        "metadata": {"story_points": 3, "type": "feature"}
    }
]

total_points = 0
for story in stories:
    task = create_task(
        title=story["title"],
        description=story["description"],
        priority=story["priority"],
        parent_task_id=sprint["id"],
        metadata=story["metadata"]
    )
    total_points += story["metadata"]["story_points"]

# Update sprint with total points
update_task(
    id=sprint["id"],
    updates={
        "metadata": {
            **sprint["metadata"],
            "story_points": total_points
        }
    }
)

# Daily standup: Check progress
sprint_tasks = query_tasks(filters={"parent_task_id": sprint["id"]})
completed = [t for t in sprint_tasks if t["status"] == "completed"]
in_progress = [t for t in sprint_tasks if t["status"] == "in_progress"]

print(f"Sprint Progress: {len(completed)}/{len(sprint_tasks)} completed")
print(f"In Progress: {len(in_progress)}")
```

### Code Review Queue

```python
# Create review tasks when PRs are opened
def on_pull_request_opened(pr_number, author, title):
    create_task(
        title=f"Review PR #{pr_number}: {title}",
        description=f"Code review requested by {author}",
        status="pending",
        priority="high",
        metadata={
            "type": "code-review",
            "pr_number": pr_number,
            "author": author,
            "url": f"https://github.com/org/repo/pull/{pr_number}"
        }
    )

# Reviewer claims a task
review_queue = query_tasks(filters={
    "status": "pending",
    "title_contains": "Review PR"
})

if review_queue:
    task = review_queue[0]
    update_task(
        id=task["id"],
        updates={
            "status": "in_progress",
            "assignee": "reviewer-alice"
        }
    )

# Complete review
update_task(
    id=task["id"],
    updates={
        "status": "completed",
        "metadata": {
            **task["metadata"],
            "reviewed_at": "2026-01-21T10:30:00Z",
            "approved": True,
            "comments": 3
        }
    }
)
```

## Instance Monitoring

### Heartbeat System

```python
import time
import threading

def heartbeat_loop(instance_id, interval=60):
    """Send heartbeat every minute"""
    while True:
        try:
            heartbeat(instance_id=instance_id)
            print(f"Heartbeat sent for {instance_id}")
        except Exception as e:
            print(f"Heartbeat failed: {e}")

        time.sleep(interval)

# Start heartbeat in background
instance_id = "claude-worker-1"
heartbeat_thread = threading.Thread(
    target=heartbeat_loop,
    args=(instance_id,),
    daemon=True
)
heartbeat_thread.start()
```

### Instance Status Dashboard

```python
# Get all instances (even inactive ones)
# Note: This requires direct database access for inactive instances
# Active instances only:
instances = list_active_instances()

print("ACTIVE INSTANCES")
print("=" * 60)

for instance in instances:
    print(f"\nInstance: {instance['instance_id']}")
    print(f"  Status: {instance['status']}")
    print(f"  Last Heartbeat: {instance['last_heartbeat']}")

    if instance['current_task_id']:
        task = get_task(instance['current_task_id'])
        print(f"  Current Task: #{task['id']} - {task['title']}")
    else:
        print(f"  Current Task: None (idle)")

    if instance['working_directory']:
        print(f"  Working Dir: {instance['working_directory']}")

    # Get task history
    completed_tasks = query_tasks(filters={
        "assignee": instance['instance_id'],
        "status": "completed"
    })
    print(f"  Completed Tasks: {len(completed_tasks)}")
```

## Advanced Queries

### Complex Filtering

```python
# Find all high-priority blocked tasks
blocked_critical = query_tasks(filters={
    "status": "blocked",
    "priority": "high"
})

# Find tasks by assignee
my_tasks = query_tasks(filters={
    "assignee": "claude-worker-1"
})

# Search by keyword
auth_tasks = query_tasks(filters={
    "title_contains": "authentication"
})

security_tasks = query_tasks(filters={
    "description_contains": "security"
})

# Find all subtasks of a parent
subtasks = query_tasks(filters={
    "parent_task_id": 5
})

# Find root tasks (no parent)
root_tasks = [
    task for task in query_tasks()
    if task["parent_task_id"] is None
]
```

### Analytics and Reporting

```python
# Get all tasks
all_tasks = query_tasks()

# Count by status
from collections import Counter

status_counts = Counter(task["status"] for task in all_tasks)
print("Tasks by Status:")
for status, count in status_counts.items():
    print(f"  {status}: {count}")

# Count by priority
priority_counts = Counter(task["priority"] for task in all_tasks)
print("\nTasks by Priority:")
for priority, count in priority_counts.items():
    print(f"  {priority}: {count}")

# Average tasks per assignee
assignees = [task["assignee"] for task in all_tasks if task["assignee"]]
assignee_counts = Counter(assignees)
print("\nTasks by Assignee:")
for assignee, count in sorted(assignee_counts.items(), key=lambda x: -x[1]):
    print(f"  {assignee}: {count}")

# Find oldest pending task
pending_tasks = [t for t in all_tasks if t["status"] == "pending"]
if pending_tasks:
    oldest = min(pending_tasks, key=lambda t: t["created_at"])
    print(f"\nOldest Pending Task: #{oldest['id']} - {oldest['title']}")
    print(f"  Created: {oldest['created_at']}")
```

### Metadata-Driven Workflows

```python
# Tag-based organization
create_task(
    title="Optimize database queries",
    priority="high",
    metadata={
        "tags": ["performance", "database", "optimization"],
        "estimated_hours": 4,
        "actual_hours": 0,
        "team": "backend"
    }
)

# Search by tag (requires custom query)
all_tasks = query_tasks()
performance_tasks = [
    task for task in all_tasks
    if task.get("metadata") and "performance" in task["metadata"].get("tags", [])
]

# Track time estimates
total_estimated = sum(
    task.get("metadata", {}).get("estimated_hours", 0)
    for task in query_tasks(filters={"status": "pending"})
)
print(f"Estimated hours remaining: {total_estimated}")

# Team-based filtering
backend_tasks = [
    task for task in all_tasks
    if task.get("metadata", {}).get("team") == "backend"
]
```

## Integration Patterns

### GitHub Issues Sync

```python
def sync_github_issue_to_task(issue):
    """Convert GitHub issue to task"""
    create_task(
        title=f"GH-{issue['number']}: {issue['title']}",
        description=issue['body'],
        priority=map_github_priority(issue['labels']),
        metadata={
            "source": "github",
            "issue_number": issue['number'],
            "url": issue['html_url'],
            "author": issue['user']['login'],
            "labels": [label['name'] for label in issue['labels']]
        }
    )

def map_github_priority(labels):
    """Map GitHub labels to task priority"""
    label_names = [l['name'].lower() for l in labels]
    if 'critical' in label_names or 'p0' in label_names:
        return 'critical'
    elif 'high' in label_names or 'p1' in label_names:
        return 'high'
    elif 'low' in label_names or 'p3' in label_names:
        return 'low'
    return 'medium'
```

### Notification System

```python
def check_overdue_tasks():
    """Find tasks that should be escalated"""
    from datetime import datetime, timedelta

    all_tasks = query_tasks(filters={"status": "in_progress"})
    overdue = []

    for task in all_tasks:
        metadata = task.get("metadata", {})
        deadline = metadata.get("deadline")

        if deadline:
            deadline_dt = datetime.fromisoformat(deadline)
            if deadline_dt < datetime.now():
                overdue.append(task)

                # Escalate priority
                if task["priority"] != "critical":
                    new_priority = {
                        "low": "medium",
                        "medium": "high",
                        "high": "critical"
                    }[task["priority"]]

                    update_task(
                        id=task["id"],
                        updates={"priority": new_priority}
                    )

    return overdue
```

## Best Practices

1. **Use Metadata Liberally**: Store any custom data you need in the metadata field
2. **Regular Heartbeats**: Send heartbeats every 1-2 minutes for accurate instance tracking
3. **Descriptive Titles**: Make task titles searchable and meaningful
4. **Proper Status Updates**: Always update task status as work progresses
5. **Task Hierarchy**: Use parent/child relationships for complex projects
6. **Unique Instance IDs**: Use descriptive, unique identifiers for instances
7. **Query Optimization**: Use specific filters to reduce data transfer
8. **Cleanup**: Regularly archive or delete completed tasks to maintain performance

## Troubleshooting Common Patterns

### Finding Stuck Tasks

```python
# Find tasks in progress for more than 24 hours
from datetime import datetime, timedelta

all_tasks = query_tasks(filters={"status": "in_progress"})
threshold = datetime.now() - timedelta(hours=24)

stuck_tasks = [
    task for task in all_tasks
    if datetime.fromisoformat(task["updated_at"]) < threshold
]

print(f"Found {len(stuck_tasks)} potentially stuck tasks")
```

### Orphaned Tasks

```python
# Find tasks with non-existent assignees
all_tasks = query_tasks()
active_instances = {i["instance_id"] for i in list_active_instances()}

orphaned = [
    task for task in all_tasks
    if task.get("assignee") and task["assignee"] not in active_instances
]

# Reassign or unassign
for task in orphaned:
    update_task(
        id=task["id"],
        updates={"assignee": None, "status": "pending"}
    )
```
