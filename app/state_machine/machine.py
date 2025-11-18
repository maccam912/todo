"""State machine for LLM-driven task management."""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.scope import Scope, get_tasks_for_scope
from app.models import TaskRecurrence, TaskStatus, TaskUrgency
from app.services.task_service import (
    complete_task,
    create_task,
    delete_task,
    get_task_by_id,
    update_task,
)

logger = logging.getLogger(__name__)


@dataclass
class PendingOperation:
    """Represents a pending operation to be committed."""

    type: Literal["create_task", "update_task", "complete_task", "delete_task"]
    target: tuple[Literal["existing", "pending"], int]
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanNote:
    """Represents a recorded plan."""

    plan: str


State = Literal["awaiting_command", "completed"] | tuple[Literal["editing_task"], tuple[Literal["existing", "pending"], int]]


class StateMachine:
    """State machine for managing LLM-driven task operations."""

    def __init__(self, scope: Scope, db: Session):
        self.scope = scope
        self.db = db
        self.state: State = "awaiting_command"
        self.pending_ops: list[PendingOperation] = []
        self.edit_context: dict[str, Any] | None = None
        self.next_pending_ref: int = 1
        self.plan_notes: list[PlanNote] = []
        self.error_count: int = 0
        self.session_id: str = str(uuid.uuid4())

    def handle_command(
        self, command: str, params: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """
        Handle a command from the LLM.

        Args:
            command: Command name
            params: Command parameters

        Returns:
            Tuple of (success, response_dict)
        """
        if self.state == "completed":
            return False, self.build_response(
                "Session already completed", error=True
            )

        # Route command to appropriate handler
        handlers = {
            "record_plan": self._handle_record_plan,
            "select_task": self._handle_select_task,
            "create_task": self._handle_create_task,
            "update_task_fields": self._handle_update_task_fields,
            "complete_task": self._handle_complete_task,
            "delete_task": self._handle_delete_task,
            "exit_editing": self._handle_exit_editing,
            "discard_all": self._handle_discard_all,
            "complete_session": self._handle_complete_session,
        }

        handler = handlers.get(command)
        if not handler:
            return False, self.build_response(
                f"Unknown command: {command}", error=True
            )

        try:
            return handler(params)
        except Exception as e:
            logger.error(f"Error handling command {command}: {e}", exc_info=True)
            self.error_count += 1
            return False, self.build_response(str(e), error=True)

    def _handle_record_plan(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle record_plan command."""
        plan = params.get("plan")
        if not plan:
            return False, self.build_response("Plan is required", error=True)

        self.plan_notes.append(PlanNote(plan=plan))
        return True, self.build_response(f"Plan recorded: {plan}")

    def _handle_select_task(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle select_task command."""
        if self.state != "awaiting_command":
            return False, self.build_response(
                "Must be in awaiting_command state to select task", error=True
            )

        target_str = params.get("target")
        if not target_str:
            return False, self.build_response("Target is required", error=True)

        # Parse target (e.g., "existing:123" or "pending:1")
        try:
            target_type, target_id = target_str.split(":", 1)
            target_id = int(target_id)
            target: tuple[Literal["existing", "pending"], int] = (target_type, target_id)  # type: ignore
        except (ValueError, AttributeError):
            return False, self.build_response(
                f"Invalid target format: {target_str}", error=True
            )

        if target_type not in ["existing", "pending"]:
            return False, self.build_response(
                f"Invalid target type: {target_type}", error=True
            )

        # Validate target exists
        if target_type == "existing":
            task = get_task_by_id(self.db, self.scope, target_id)
            if not task:
                return False, self.build_response(
                    f"Task {target_id} not found", error=True
                )
            self.edit_context = {"task_id": target_id, "task": task}
        else:  # pending
            # Find pending operation
            pending_op = next(
                (
                    op
                    for op in self.pending_ops
                    if op.target == target
                ),
                None,
            )
            if not pending_op:
                return False, self.build_response(
                    f"Pending task {target_id} not found", error=True
                )
            self.edit_context = {"pending_ref": target_id, "operation": pending_op}

        self.state = ("editing_task", target)
        return True, self.build_response(f"Selected task: {target_str}")

    def _handle_create_task(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle create_task command."""
        if not params.get("title"):
            return False, self.build_response("Title is required", error=True)

        # Stage the operation
        ref = self.next_pending_ref
        target: tuple[Literal["pending"], int] = ("pending", ref)
        self.pending_ops.append(
            PendingOperation(type="create_task", target=target, attrs=params)
        )
        self.next_pending_ref += 1

        return True, self.build_response(
            f"Task creation staged with pending_ref {ref}",
            echo={"pending_ref": ref, "title": params.get("title")},
        )

    def _handle_update_task_fields(
        self, params: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """Handle update_task_fields command."""
        if not isinstance(self.state, tuple) or self.state[0] != "editing_task":
            return False, self.build_response(
                "Must be in editing_task state to update fields", error=True
            )

        target = self.state[1]

        # Stage the operation
        self.pending_ops.append(
            PendingOperation(type="update_task", target=target, attrs=params)
        )

        return True, self.build_response(
            f"Update staged for {target[0]}:{target[1]}"
        )

    def _handle_complete_task(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle complete_task command."""
        if not isinstance(self.state, tuple) or self.state[0] != "editing_task":
            return False, self.build_response(
                "Must be in editing_task state to complete task", error=True
            )

        target = self.state[1]

        # Stage the operation
        self.pending_ops.append(
            PendingOperation(type="complete_task", target=target, attrs={})
        )

        return True, self.build_response(
            f"Completion staged for {target[0]}:{target[1]}"
        )

    def _handle_delete_task(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle delete_task command."""
        if not isinstance(self.state, tuple) or self.state[0] != "editing_task":
            return False, self.build_response(
                "Must be in editing_task state to delete task", error=True
            )

        target = self.state[1]

        # Stage the operation
        self.pending_ops.append(
            PendingOperation(type="delete_task", target=target, attrs={})
        )

        return True, self.build_response(
            f"Deletion staged for {target[0]}:{target[1]}"
        )

    def _handle_exit_editing(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle exit_editing command."""
        if not isinstance(self.state, tuple) or self.state[0] != "editing_task":
            return False, self.build_response(
                "Not in editing mode", error=True
            )

        self.state = "awaiting_command"
        self.edit_context = None

        return True, self.build_response("Exited editing mode")

    def _handle_discard_all(self, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Handle discard_all command."""
        self.pending_ops.clear()
        self.plan_notes.clear()
        self.next_pending_ref = 1
        self.state = "awaiting_command"
        self.edit_context = None

        return True, self.build_response("All operations discarded")

    def _handle_complete_session(
        self, params: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """Handle complete_session command."""
        # Commit all pending operations
        try:
            summary = self.commit_operations()
            self.state = "completed"
            return True, self.build_response(
                "Session completed successfully", commit_summary=summary
            )
        except Exception as e:
            logger.error(f"Error committing operations: {e}", exc_info=True)
            return False, self.build_response(
                f"Failed to commit operations: {e}", error=True
            )

    def commit_operations(self) -> dict[str, Any]:
        """
        Commit all pending operations in a single transaction.

        Returns:
            Summary of committed operations

        Raises:
            Exception: If any operation fails
        """
        pending_map: dict[int, int] = {}  # Maps pending refs to created IDs
        summary = {
            "created": [],
            "updated": [],
            "deleted": [],
            "completed": [],
        }

        for op in self.pending_ops:
            if op.type == "create_task":
                # Create task
                task = create_task(
                    self.db,
                    self.scope,
                    **self._normalize_task_attrs(op.attrs),
                )
                pending_map[op.target[1]] = task.id
                summary["created"].append({"id": task.id, "title": task.title})

            elif op.type == "update_task":
                task_id = self._resolve_target(op.target, pending_map)
                task = update_task(
                    self.db,
                    self.scope,
                    task_id,
                    self._normalize_task_attrs(op.attrs),
                )
                summary["updated"].append({"id": task.id, "title": task.title})

            elif op.type == "complete_task":
                task_id = self._resolve_target(op.target, pending_map)
                task = complete_task(self.db, self.scope, task_id)
                summary["completed"].append({"id": task.id, "title": task.title})

            elif op.type == "delete_task":
                task_id = self._resolve_target(op.target, pending_map)
                task = get_task_by_id(self.db, self.scope, task_id)
                if task:
                    delete_task(self.db, self.scope, task_id)
                    summary["deleted"].append({"id": task_id, "title": task.title})

        return summary

    def _resolve_target(
        self, target: tuple[Literal["existing", "pending"], int], pending_map: dict[int, int]
    ) -> int:
        """Resolve a target to an actual task ID."""
        if target[0] == "existing":
            return target[1]
        else:  # pending
            if target[1] not in pending_map:
                raise ValueError(f"Pending task {target[1]} not yet created")
            return pending_map[target[1]]

    def _normalize_task_attrs(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Normalize task attributes for service layer."""
        normalized = attrs.copy()

        # Convert date strings to date objects
        for date_field in ["due_date", "deferred_until"]:
            if date_field in normalized and isinstance(normalized[date_field], str):
                try:
                    normalized[date_field] = date.fromisoformat(normalized[date_field])
                except ValueError:
                    normalized[date_field] = None

        # Convert enum strings to enum values
        if "status" in normalized:
            normalized["task_status"] = normalized.pop("status")

        return normalized

    def build_response(
        self,
        message: str,
        error: bool = False,
        echo: dict[str, Any] | None = None,
        commit_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a response dictionary."""
        response = {
            "state": self._serialize_state(),
            "message": message,
            "open_tasks": self._get_open_tasks(),
            "pending_operations": [
                {
                    "type": op.type,
                    "target": f"{op.target[0]}:{op.target[1]}",
                    "attrs": op.attrs,
                }
                for op in self.pending_ops
            ],
            "available_commands": self._get_available_commands(),
        }

        if error:
            response["error"] = True

        if echo:
            response["echo"] = echo

        if commit_summary:
            response["commit_summary"] = commit_summary

        return response

    def _serialize_state(self) -> str:
        """Serialize current state to string."""
        if isinstance(self.state, tuple):
            return f"{self.state[0]}:{self.state[1][0]}:{self.state[1][1]}"
        return self.state

    def _get_open_tasks(self) -> list[dict[str, Any]]:
        """Get open tasks for context."""
        tasks = get_tasks_for_scope(self.db, self.scope)
        return [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "urgency": task.urgency,
                "due_date": str(task.due_date) if task.due_date else None,
            }
            for task in tasks[:20]  # Limit to 20 tasks
        ]

    def _get_available_commands(self) -> list[str]:
        """Get list of available commands based on current state."""
        if self.state == "completed":
            return []

        if self.state == "awaiting_command":
            return [
                "record_plan",
                "select_task",
                "create_task",
                "discard_all",
                "complete_session",
            ]

        if isinstance(self.state, tuple) and self.state[0] == "editing_task":
            return [
                "update_task_fields",
                "complete_task",
                "delete_task",
                "exit_editing",
                "discard_all",
                "complete_session",
            ]

        return []

    def get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        user_prefs = ""
        if self.scope.preference and self.scope.preference.prompt_preferences:
            user_prefs = f"\n\n## User Preferences\n{self.scope.preference.prompt_preferences}"

        return f"""You manage SmartTodo tasks strictly through the provided function-call tools.

## Core Rules
1. Every reply MUST be exactly one function call defined in `available_commands`.
2. Read the state snapshot each turn; `available_commands` is the source of truth for what you can call.
3. To change, complete, or delete an existing task you MUST call `select_task` first.
4. New tasks are staged with `create_task`; existing tasks accumulate staged changes until you `complete_session` (commit) or `discard_all`.
5. Whenever solving the request requires more than one command, call `record_plan` first to capture the steps you intend to take.
6. `complete_session` MUST be the final command you ever issue in a session.

## Task Target Format
- Existing tasks: "existing:123" where 123 is the task ID
- Pending tasks: "pending:1" where 1 is the pending reference number

## Status Values: todo, in_progress, done
## Urgency Values: low, normal, high, critical
## Recurrence Values: none, daily, weekly, monthly, yearly{user_prefs}"""
