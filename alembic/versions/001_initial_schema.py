"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create CITEXT extension
    op.execute('CREATE EXTENSION IF NOT EXISTS citext')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', postgresql.CITEXT(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create users_tokens table
    op.create_table(
        'users_tokens',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token', sa.LargeBinary(), nullable=False),
        sa.Column('context', sa.String(), nullable=False),
        sa.Column('authenticated_at', sa.DateTime(), nullable=True),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_tokens_id'), 'users_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_users_tokens_user_id'), 'users_tokens', ['user_id'], unique=False)
    op.create_index('idx_users_tokens_context_token', 'users_tokens', ['context', 'token'], unique=True)

    # Create user_access_tokens table
    op.create_table(
        'user_access_tokens',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(), nullable=False),
        sa.Column('token_prefix', sa.String(), nullable=False),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_access_tokens_id'), 'user_access_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_user_access_tokens_user_id'), 'user_access_tokens', ['user_id'], unique=False)
    op.create_index('idx_user_access_tokens_hash', 'user_access_tokens', ['token_hash'], unique=True)

    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('prompt_preferences', sa.String(length=2000), nullable=True),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_id'), 'user_preferences', ['id'], unique=False)
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'], unique=True)

    # Create groups table
    op.create_table(
        'groups',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('created_by_user_id', sa.BigInteger(), nullable=False),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=False)
    op.create_index('idx_groups_name', 'groups', ['name'], unique=True)
    op.create_index('idx_groups_created_by', 'groups', ['created_by_user_id'], unique=False)

    # Create group_memberships table
    op.create_table(
        'group_memberships',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('group_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('member_group_id', sa.BigInteger(), nullable=True),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND member_group_id IS NULL) OR (user_id IS NULL AND member_group_id IS NOT NULL)',
            name='exactly_one_member_type'
        ),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'user_id', name='idx_group_memberships_group_user'),
        sa.UniqueConstraint('group_id', 'member_group_id', name='idx_group_memberships_group_group')
    )
    op.create_index(op.f('ix_group_memberships_id'), 'group_memberships', ['id'], unique=False)
    op.create_index(op.f('ix_group_memberships_group_id'), 'group_memberships', ['group_id'], unique=False)
    op.create_index(op.f('ix_group_memberships_user_id'), 'group_memberships', ['user_id'], unique=False)
    op.create_index(op.f('ix_group_memberships_member_group_id'), 'group_memberships', ['member_group_id'], unique=False)

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('assignee_id', sa.BigInteger(), nullable=True),
        sa.Column('assigned_group_id', sa.BigInteger(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=10000), nullable=True),
        sa.Column('notes', sa.String(length=10000), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='todo'),
        sa.Column('urgency', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('deferred_until', sa.Date(), nullable=True),
        sa.Column('recurrence', sa.String(length=20), nullable=False, server_default='none'),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            'NOT (assignee_id IS NOT NULL AND assigned_group_id IS NOT NULL)',
            name='check_single_assignment'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_group_id'], ['groups.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)
    op.create_index(op.f('ix_tasks_user_id'), 'tasks', ['user_id'], unique=False)
    op.create_index(op.f('ix_tasks_assignee_id'), 'tasks', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_tasks_assigned_group_id'), 'tasks', ['assigned_group_id'], unique=False)
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
    op.create_index(op.f('ix_tasks_due_date'), 'tasks', ['due_date'], unique=False)
    op.create_index(op.f('ix_tasks_deferred_until'), 'tasks', ['deferred_until'], unique=False)

    # Create task_dependencies table
    op.create_table(
        'task_dependencies',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('blocked_task_id', sa.BigInteger(), nullable=False),
        sa.Column('prereq_task_id', sa.BigInteger(), nullable=False),
        sa.Column('inserted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('blocked_task_id != prereq_task_id', name='no_self_reference'),
        sa.ForeignKeyConstraint(['blocked_task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prereq_task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocked_task_id', 'prereq_task_id', name='idx_task_dependencies_unique')
    )
    op.create_index(op.f('ix_task_dependencies_id'), 'task_dependencies', ['id'], unique=False)
    op.create_index('idx_task_dependencies_blocked', 'task_dependencies', ['blocked_task_id'], unique=False)
    op.create_index('idx_task_dependencies_prereq', 'task_dependencies', ['prereq_task_id'], unique=False)


def downgrade() -> None:
    op.drop_table('task_dependencies')
    op.drop_table('tasks')
    op.drop_table('group_memberships')
    op.drop_table('groups')
    op.drop_table('user_preferences')
    op.drop_table('user_access_tokens')
    op.drop_table('users_tokens')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS citext')
