"""Conversation service for managing LLM-driven task processing."""

import logging
from typing import Any

from opentelemetry import trace
from sqlalchemy.orm import Session

from todo.config import Settings
from todo.core.scope import Scope
from todo.schemas.task import TaskCommandResponse
from todo.services.llm_service import (
    LLMService,
    build_function_schemas,
    extract_function_call,
)
from todo.state_machine import StateMachine
from todo.telemetry import create_agent_span_attributes, set_span_attributes

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ConversationService:
    """Service for managing LLM conversations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = LLMService(settings)

    async def process_request(
        self, db: Session, scope: Scope, text: str
    ) -> tuple[list[TaskCommandResponse], str, str]:
        """
        Process a natural language request using LLM.

        Args:
            db: Database session
            scope: Authorization scope
            text: Natural language request

        Returns:
            Tuple of (executed_actions, message, session_id)
        """
        machine = StateMachine(scope, db)
        session_id = machine.session_id

        with tracer.start_as_current_span("agent.session") as span:
            # Set OpenInference attributes for agent span
            attributes = create_agent_span_attributes(
                session_id=session_id,
                user_id=str(scope.user.id),
                input_value=text,
            )
            set_span_attributes(span, **attributes)

            # Initialize conversation
            messages: list[dict[str, Any]] = []
            actions: list[TaskCommandResponse] = []
            system_prompt = machine.get_system_prompt()
            function_schemas = build_function_schemas()

            # Initial user message with context
            initial_message = self._build_initial_message(text, machine)
            messages.append({"role": "user", "content": initial_message})

            # Conversation loop
            for round_num in range(self.settings.max_conversation_rounds):
                logger.info(
                    f"Conversation round {round_num + 1}/{self.settings.max_conversation_rounds}"
                )

                # Call LLM
                try:
                    response = await self.llm_service.chat_completion(
                        messages=messages,
                        tools=function_schemas,
                        system_prompt=system_prompt,
                        session_id=session_id,
                        user_id=str(scope.user.id),
                    )
                except Exception as e:
                    logger.error(f"LLM request failed: {e}")
                    error_message = f"LLM request failed: {str(e)}"
                    set_span_attributes(span, output_value=error_message, error=True)
                    raise Exception(error_message) from e

                # Extract function call
                function_call = extract_function_call(response)
                if not function_call:
                    logger.warning("No function call in LLM response")
                    break

                command, params = function_call
                logger.info(f"Executing command: {command} with params: {params}")

                # Execute command on state machine
                success, result = machine.handle_command(command, params)

                # Record action
                action = TaskCommandResponse(
                    command=command,
                    target=result.get("echo", {}).get("pending_ref"),
                    attributes=params,
                    result=result.get("message", ""),
                )
                actions.append(action)

                # Add assistant message to conversation
                messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": f"call_{round_num}",
                                "type": "function",
                                "function": {
                                    "name": command,
                                    "arguments": str(params),
                                },
                            }
                        ],
                    }
                )

                # Add tool response to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": f"call_{round_num}",
                        "content": str(result),
                    }
                )

                # Check if session is completed
                if machine.state == "completed":
                    logger.info("Session completed successfully")
                    break

                # Check error count
                if not success:
                    machine.error_count += 1
                    if machine.error_count >= self.settings.max_command_errors:
                        logger.error("Too many errors, terminating session")
                        break

            # Build final message
            final_message = self._build_final_message(actions, machine)

            # Set output on agent span
            set_span_attributes(
                span,
                output_value=str(
                    {
                        "state": machine._serialize_state(),
                        "executed_commands": len(actions),
                        "message": final_message,
                    }
                ),
            )

            return actions, final_message, session_id

    async def close(self):
        """Close the conversation service."""
        await self.llm_service.close()

    def _build_initial_message(self, text: str, machine: StateMachine) -> str:
        """Build the initial message with context."""
        state = machine.build_response("Initial state")

        return f"""User request: {text}

Available commands: {", ".join(state["available_commands"])}

Open tasks (max 20):
{self._format_tasks(state["open_tasks"])}

Current state: {state["state"]}
Pending operations: {len(state["pending_operations"])}
"""

    def _format_tasks(self, tasks: list[dict[str, Any]]) -> str:
        """Format tasks for display."""
        if not tasks:
            return "No open tasks"

        lines = []
        for task in tasks:
            line = f"- [{task['id']}] {task['title']} (status: {task['status']}, urgency: {task['urgency']})"
            if task.get("due_date"):
                line += f" [due: {task['due_date']}]"
            lines.append(line)

        return "\n".join(lines)

    def _build_final_message(
        self, actions: list[TaskCommandResponse], machine: StateMachine
    ) -> str:
        """Build final message summarizing actions."""
        if not actions:
            return "No actions performed"

        action_count = len(actions)
        state = machine._serialize_state()

        if state == "completed":
            return f"Successfully performed {action_count} action{'s' if action_count != 1 else ''} and committed changes"
        else:
            return f"Performed {action_count} action{'s' if action_count != 1 else ''} but did not complete session"
