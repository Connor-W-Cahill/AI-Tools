#!/usr/bin/env python3
"""
Database Inspection Tool for Task State Server

Quick CLI tool to view database contents without needing sqlite3.
"""

import sys
import json
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent))
import server


def print_tasks():
    """Display all tasks."""
    tasks = server.query_tasks()

    if not tasks:
        print("No tasks found.")
        return

    print(f"\n{'='*80}")
    print(f"TASKS ({len(tasks)} total)")
    print(f"{'='*80}\n")

    for task in tasks:
        print(f"ID: {task['id']}")
        print(f"  Title: {task['title']}")
        if task['description']:
            print(f"  Description: {task['description']}")
        print(f"  Status: {task['status']}")
        print(f"  Priority: {task['priority']}")
        if task['assignee']:
            print(f"  Assignee: {task['assignee']}")
        if task['parent_task_id']:
            print(f"  Parent Task: {task['parent_task_id']}")
        if task.get('subtask_ids'):
            print(f"  Subtasks: {task['subtask_ids']}")
        print(f"  Created: {task['created_at']}")
        print(f"  Updated: {task['updated_at']}")
        if task['completed_at']:
            print(f"  Completed: {task['completed_at']}")
        if task['metadata']:
            print(f"  Metadata: {json.dumps(task['metadata'], indent=4)}")
        print()


def print_instances():
    """Display all instances."""
    # Get all instances (not just active)
    conn = server.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM instance_states ORDER BY last_heartbeat DESC")
    rows = cursor.fetchall()

    instances = []
    for row in rows:
        instance = server.row_to_dict(row)
        instance['metadata'] = server.deserialize_metadata(instance['metadata'])
        instances.append(instance)

    if not instances:
        print("No instances found.")
        return

    print(f"\n{'='*80}")
    print(f"INSTANCES ({len(instances)} total)")
    print(f"{'='*80}\n")

    for instance in instances:
        print(f"Instance ID: {instance['instance_id']}")
        print(f"  Status: {instance['status']}")
        print(f"  Last Heartbeat: {instance['last_heartbeat']}")
        if instance['current_task_id']:
            print(f"  Current Task: {instance['current_task_id']}")
        if instance['working_directory']:
            print(f"  Working Directory: {instance['working_directory']}")
        if instance['metadata']:
            print(f"  Metadata: {json.dumps(instance['metadata'], indent=4)}")
        print()


def print_statistics():
    """Display database statistics."""
    tasks = server.query_tasks()

    print(f"\n{'='*80}")
    print("STATISTICS")
    print(f"{'='*80}\n")

    # Status breakdown
    from collections import Counter
    status_counts = Counter(task['status'] for task in tasks)

    print("Tasks by Status:")
    for status in ['pending', 'in_progress', 'blocked', 'completed']:
        count = status_counts.get(status, 0)
        print(f"  {status:15} {count:5}")

    print()

    # Priority breakdown
    priority_counts = Counter(task['priority'] for task in tasks)

    print("Tasks by Priority:")
    for priority in ['critical', 'high', 'medium', 'low']:
        count = priority_counts.get(priority, 0)
        print(f"  {priority:15} {count:5}")

    print()

    # Assignee breakdown
    assignees = [task['assignee'] for task in tasks if task['assignee']]
    assignee_counts = Counter(assignees)

    if assignees:
        print("Tasks by Assignee:")
        for assignee, count in sorted(assignee_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {assignee:30} {count:5}")
        print()

    # Instances
    instances = server.list_active_instances()
    print(f"Active Instances: {len(instances)}")
    print()


def print_schema():
    """Display database schema."""
    conn = server.get_db()
    cursor = conn.cursor()

    print(f"\n{'='*80}")
    print("DATABASE SCHEMA")
    print(f"{'='*80}\n")

    # Get table info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        print(f"Table: {table}")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        for col in columns:
            col_id, name, type_, notnull, default, pk = col
            nullable = "NOT NULL" if notnull else "NULL"
            primary = "PRIMARY KEY" if pk else ""
            default_str = f"DEFAULT {default}" if default else ""
            print(f"  {name:20} {type_:15} {nullable:10} {primary:15} {default_str}")
        print()

    # Get indices
    print("Indices:")
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
    indices = cursor.fetchall()

    for idx_name, tbl_name in indices:
        if not idx_name.startswith('sqlite_'):  # Skip auto-created indices
            cursor.execute(f"PRAGMA index_info({idx_name})")
            idx_info = cursor.fetchall()
            columns = [row[2] for row in idx_info]
            print(f"  {idx_name:30} ON {tbl_name} ({', '.join(columns)})")
    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect Task State Server Database",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='all',
        choices=['all', 'tasks', 'instances', 'stats', 'schema'],
        help='What to display (default: all)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    # Initialize database
    server.get_db()

    if args.json:
        # JSON output mode
        data = {}
        if args.command in ['all', 'tasks']:
            data['tasks'] = server.query_tasks()
        if args.command in ['all', 'instances']:
            conn = server.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM instance_states")
            rows = cursor.fetchall()
            instances = []
            for row in rows:
                instance = server.row_to_dict(row)
                instance['metadata'] = server.deserialize_metadata(instance['metadata'])
                instances.append(instance)
            data['instances'] = instances
        print(json.dumps(data, indent=2, default=str))
    else:
        # Pretty-printed output
        if args.command in ['all', 'tasks']:
            print_tasks()

        if args.command in ['all', 'instances']:
            print_instances()

        if args.command in ['all', 'stats']:
            print_statistics()

        if args.command == 'schema':
            print_schema()

        if args.command == 'all':
            print_schema()


if __name__ == "__main__":
    main()
