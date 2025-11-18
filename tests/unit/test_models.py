"""Unit tests for database models."""

from sqlalchemy.orm import Session

from todo.models.group import Group
from todo.models.task import Task
from todo.models.user import User


def test_user_model(db_session: Session):
    """Test User model creation."""
    user = User(
        username="testuser",
        hashed_password="hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.hashed_password == "hashed_password"
    assert user.inserted_at is not None
    assert user.updated_at is not None


def test_task_model(db_session: Session):
    """Test Task model creation."""
    # Create a user first
    user = User(username="testuser", hashed_password="hashed_password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create a task
    task = Task(
        title="Test Task",
        description="Test Description",
        status="todo",
        urgency="medium",
        user_id=user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.status == "todo"
    assert task.urgency == "medium"
    assert task.user_id == user.id
    assert task.inserted_at is not None


def test_group_model(db_session: Session):
    """Test Group model creation."""
    # Create owner
    owner = User(username="owner", hashed_password="hashed_password")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # Create group
    group = Group(
        name="Test Group",
        description="Test Description",
        created_by_user_id=owner.id,
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    assert group.id is not None
    assert group.name == "Test Group"
    assert group.description == "Test Description"
    assert group.created_by_user_id == owner.id
    assert group.inserted_at is not None


def test_task_relationships(db_session: Session):
    """Test Task model relationships."""
    from todo.models.task import TaskDependency

    # Create owner
    owner = User(username="owner", hashed_password="hashed_password")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # Create tasks with dependency
    task1 = Task(
        title="Task 1",
        status="todo",
        urgency="normal",
        user_id=owner.id,
    )
    db_session.add(task1)
    db_session.commit()
    db_session.refresh(task1)

    task2 = Task(
        title="Task 2",
        status="todo",
        urgency="normal",
        user_id=owner.id,
    )
    db_session.add(task2)
    db_session.commit()
    db_session.refresh(task2)

    # Create dependency: task2 is blocked by task1 (task1 is a prerequisite for task2)
    dependency = TaskDependency(
        blocked_task_id=task2.id,
        prereq_task_id=task1.id,
    )
    db_session.add(dependency)
    db_session.commit()
    db_session.refresh(task2)

    # Verify task2 is blocked by task1
    assert len(task2.blocked_by) == 1
    assert task2.blocked_by[0].prereq_task_id == task1.id
