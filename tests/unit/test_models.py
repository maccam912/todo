"""Unit tests for database models."""
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from todo.models.user import User
from todo.models.task import Task
from todo.models.group import Group


def test_user_model(db_session: Session):
    """Test User model creation."""
    user = User(
        username="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.password_hash == "hashed_password"
    assert user.created_at is not None
    assert user.updated_at is not None


def test_task_model(db_session: Session):
    """Test Task model creation."""
    # Create a user first
    user = User(username="testuser", password_hash="hashed_password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create a task
    task = Task(
        title="Test Task",
        description="Test Description",
        status="todo",
        urgency="medium",
        owner_id=user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.status == "todo"
    assert task.urgency == "medium"
    assert task.owner_id == user.id
    assert task.created_at is not None


def test_group_model(db_session: Session):
    """Test Group model creation."""
    # Create owner
    owner = User(username="owner", password_hash="hashed_password")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # Create group
    group = Group(
        name="Test Group",
        description="Test Description",
        owner_id=owner.id,
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    assert group.id is not None
    assert group.name == "Test Group"
    assert group.description == "Test Description"
    assert group.owner_id == owner.id
    assert group.created_at is not None


def test_task_relationships(db_session: Session):
    """Test Task model relationships."""
    # Create owner
    owner = User(username="owner", password_hash="hashed_password")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # Create tasks with dependency
    task1 = Task(
        title="Task 1",
        status="todo",
        urgency="medium",
        owner_id=owner.id,
    )
    db_session.add(task1)
    db_session.commit()
    db_session.refresh(task1)

    task2 = Task(
        title="Task 2",
        status="todo",
        urgency="medium",
        owner_id=owner.id,
    )
    task2.prerequisite_tasks.append(task1)
    db_session.add(task2)
    db_session.commit()
    db_session.refresh(task2)

    assert len(task2.prerequisite_tasks) == 1
    assert task2.prerequisite_tasks[0].id == task1.id
