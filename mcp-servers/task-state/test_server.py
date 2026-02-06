#!/usr/bin/env python3
"""
Test script for Task State Server

Runs comprehensive tests to verify all functionality works correctly.
"""

import sqlite3
import json
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent))

import server

def reset_database():
    """Reset database for testing."""
    db_path = Path(__file__).parent / "tasks.db"
    if db_path.exists():
        db_path.unlink()
    server._db_connection = None
    print("✓ Database reset")

def test_task_creation():
    """Test creating tasks."""
    print("\n=== Testing Task Creation ===")

    task1 = server.create_task(
        title="Test Task 1",
        description="This is a test task",
        priority="high"
    )
    assert task1['title'] == "Test Task 1"
    assert task1['priority'] == "high"
    assert task1['status'] == "pending"
    print(f"✓ Created task {task1['id']}: {task1['title']}")

    task2 = server.create_task(
        title="Test Subtask",
        parent_task_id=task1['id'],
        metadata={"category": "testing", "tags": ["automated"]}
    )
    assert task2['parent_task_id'] == task1['id']
    assert task2['metadata']['category'] == "testing"
    print(f"✓ Created subtask {task2['id']} under task {task1['id']}")

    return task1, task2

def test_task_updates():
    """Test updating tasks."""
    print("\n=== Testing Task Updates ===")

    task = server.create_task(title="Update Test")
    original_id = task['id']

    updated = server.update_task(original_id, {
        "status": "in_progress",
        "assignee": "test-agent",
        "metadata": {"progress": 50}
    })

    assert updated['id'] == original_id
    assert updated['status'] == "in_progress"
    assert updated['assignee'] == "test-agent"
    assert updated['metadata']['progress'] == 50
    print(f"✓ Updated task {original_id} successfully")

    # Test completing task
    completed = server.update_task(original_id, {"status": "completed"})
    assert completed['status'] == "completed"
    assert completed['completed_at'] is not None
    print(f"✓ Marked task {original_id} as completed")

def test_task_retrieval():
    """Test getting and querying tasks."""
    print("\n=== Testing Task Retrieval ===")

    # Create test data
    task1 = server.create_task(title="High Priority", priority="high", status="pending")
    task2 = server.create_task(title="Medium Priority", priority="medium", status="in_progress")
    task3 = server.create_task(title="Low Priority", priority="low", status="completed")

    # Test get_task
    retrieved = server.get_task(task1['id'])
    assert retrieved['title'] == "High Priority"
    print(f"✓ Retrieved task {task1['id']}")

    # Test query with filters
    pending_tasks = server.query_tasks({"status": "pending"})
    assert len(pending_tasks) >= 1
    assert any(t['id'] == task1['id'] for t in pending_tasks)
    print(f"✓ Queried pending tasks: found {len(pending_tasks)}")

    high_priority = server.query_tasks({"priority": "high"})
    assert any(t['id'] == task1['id'] for t in high_priority)
    print(f"✓ Queried high priority tasks: found {len(high_priority)}")

    # Test search
    search_results = server.query_tasks({"title_contains": "Priority"})
    assert len(search_results) >= 3
    print(f"✓ Search by title: found {len(search_results)}")

def test_task_deletion():
    """Test deleting tasks."""
    print("\n=== Testing Task Deletion ===")

    parent = server.create_task(title="Parent Task")
    child1 = server.create_task(title="Child 1", parent_task_id=parent['id'])
    child2 = server.create_task(title="Child 2", parent_task_id=parent['id'])

    # Delete parent (should cascade to children)
    result = server.delete_task(parent['id'])
    assert result['success'] == True
    print(f"✓ Deleted parent task {parent['id']}")

    # Verify children are also deleted
    try:
        server.get_task(child1['id'])
        assert False, "Child task should have been deleted"
    except ValueError:
        print(f"✓ Verified cascade delete of child tasks")

def test_instance_management():
    """Test instance state management."""
    print("\n=== Testing Instance Management ===")

    # Test heartbeat (auto-creates instance)
    instance = server.heartbeat("test-instance-1")
    assert instance['instance_id'] == "test-instance-1"
    assert instance['status'] == "active"
    print(f"✓ Created instance via heartbeat: {instance['instance_id']}")

    # Test set_instance_state
    task = server.create_task(title="Instance Test Task")
    updated_state = server.set_instance_state("test-instance-1", {
        "current_task_id": task['id'],
        "status": "busy",
        "working_directory": "/test/path",
        "metadata": {"session": "test-session"}
    })

    assert updated_state['current_task_id'] == task['id']
    assert updated_state['status'] == "busy"
    assert updated_state['working_directory'] == "/test/path"
    print(f"✓ Updated instance state")

    # Test get_instance_state
    retrieved_state = server.get_instance_state("test-instance-1")
    assert retrieved_state['current_task_id'] == task['id']
    print(f"✓ Retrieved instance state")

    # Create multiple instances
    server.heartbeat("test-instance-2")
    server.heartbeat("test-instance-3")

    # Test list_active_instances
    active = server.list_active_instances()
    assert len(active) >= 3
    print(f"✓ Listed active instances: {len(active)}")

def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")

    # Test invalid task ID
    try:
        server.get_task(99999)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e)
        print("✓ Handles invalid task ID")

    # Test invalid status
    try:
        server.create_task(title="Test", status="invalid_status")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid status" in str(e)
        print("✓ Validates task status")

    # Test invalid priority
    try:
        server.create_task(title="Test", priority="invalid_priority")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid priority" in str(e)
        print("✓ Validates task priority")

    # Test invalid parent_task_id
    try:
        server.create_task(title="Test", parent_task_id=99999)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "does not exist" in str(e)
        print("✓ Validates parent task exists")

def test_metadata_handling():
    """Test JSON metadata handling."""
    print("\n=== Testing Metadata Handling ===")

    complex_metadata = {
        "tags": ["important", "urgent"],
        "links": {
            "github": "https://github.com/example",
            "jira": "PROJ-123"
        },
        "custom_fields": {
            "estimate_hours": 5,
            "actual_hours": 3.5
        }
    }

    task = server.create_task(
        title="Metadata Test",
        metadata=complex_metadata
    )

    retrieved = server.get_task(task['id'])
    assert retrieved['metadata']['tags'] == ["important", "urgent"]
    assert retrieved['metadata']['links']['github'] == "https://github.com/example"
    assert retrieved['metadata']['custom_fields']['estimate_hours'] == 5
    print("✓ Complex metadata preserved correctly")

def test_task_hierarchy():
    """Test task hierarchy features."""
    print("\n=== Testing Task Hierarchy ===")

    # Create hierarchy: Project > Features > Tasks
    project = server.create_task(title="New Project")
    feature1 = server.create_task(title="Feature 1", parent_task_id=project['id'])
    feature2 = server.create_task(title="Feature 2", parent_task_id=project['id'])
    task1 = server.create_task(title="Task 1.1", parent_task_id=feature1['id'])
    task2 = server.create_task(title="Task 1.2", parent_task_id=feature1['id'])

    # Get project and verify subtasks
    project_data = server.get_task(project['id'])
    assert len(project_data['subtask_ids']) == 2
    print(f"✓ Project has {len(project_data['subtask_ids'])} features")

    feature1_data = server.get_task(feature1['id'])
    assert len(feature1_data['subtask_ids']) == 2
    print(f"✓ Feature has {len(feature1_data['subtask_ids'])} tasks")

    # Query by parent
    feature_tasks = server.query_tasks({"parent_task_id": feature1['id']})
    assert len(feature_tasks) == 2
    print(f"✓ Queried subtasks: found {len(feature_tasks)}")

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Task State Server - Test Suite")
    print("=" * 60)

    try:
        reset_database()
        test_task_creation()
        test_task_updates()
        test_task_retrieval()
        test_task_deletion()
        test_instance_management()
        test_error_handling()
        test_metadata_handling()
        test_task_hierarchy()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
