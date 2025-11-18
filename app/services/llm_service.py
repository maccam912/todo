"""LLM service for interacting with OpenRouter API."""
import json
import logging
from typing import Any

import httpx
from opentelemetry import trace

from app.config import Settings
from app.telemetry import create_llm_span_attributes, set_span_attributes

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class LLMService:
    """Service for interacting with LLM providers via OpenRouter."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=settings.llm_timeout)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to OpenRouter.

        Args:
            messages: List of chat messages
            tools: List of available tools/functions
            system_prompt: System prompt
            session_id: Optional session ID for tracing
            user_id: Optional user ID for tracing

        Returns:
            LLM response

        Raises:
            Exception: If request fails
        """
        with tracer.start_as_current_span("llm.chat_completion") as span:
            # Set OpenInference attributes
            attributes = create_llm_span_attributes(
                model=self.settings.llm_model,
                system_prompt=system_prompt,
                input_messages=messages,
                session_id=session_id,
                user_id=user_id,
                tools=[tool["function"]["name"] for tool in tools],
            )
            set_span_attributes(span, **attributes)

            # Build request
            request_data = {
                "model": self.settings.llm_model,
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": self.settings.llm_temperature,
            }

            # Build headers
            headers = {
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            }

            # Add OpenRouter-specific headers
            if self.settings.llm_provider == "openrouter":
                headers["HTTP-Referer"] = self.settings.openrouter_site_url
                headers["X-Title"] = self.settings.openrouter_app_name

            # Make request
            try:
                response = await self.client.post(
                    f"{self.settings.llm_base_url}/chat/completions",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()

                # Extract output messages for tracing
                output_messages = []
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    message = choice.get("message", {})
                    output_messages.append(
                        {
                            "role": message.get("role", "assistant"),
                            "content": message.get("content", ""),
                            "tool_calls": message.get("tool_calls", []),
                            "finish_reason": choice.get("finish_reason", ""),
                        }
                    )

                # Update span with output
                span.set_attribute(
                    "llm.output_messages", json.dumps(output_messages)
                )
                span.set_attribute(
                    "output.value",
                    json.dumps(output_messages[0]) if output_messages else "",
                )

                logger.info(
                    f"LLM request successful: model={self.settings.llm_model}, "
                    f"tokens={result.get('usage', {})}"
                )

                return result

            except httpx.HTTPError as e:
                logger.error(f"LLM request failed: {e}")
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise Exception(f"LLM request failed: {e}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


def extract_function_call(response: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """
    Extract function call from LLM response.

    Args:
        response: LLM response

    Returns:
        Tuple of (function_name, arguments) if function call exists, None otherwise
    """
    if "choices" not in response or len(response["choices"]) == 0:
        return None

    choice = response["choices"][0]
    message = choice.get("message", {})

    # Check for tool calls (OpenAI format)
    tool_calls = message.get("tool_calls", [])
    if tool_calls and len(tool_calls) > 0:
        tool_call = tool_calls[0]
        function = tool_call.get("function", {})
        function_name = function.get("name")
        arguments_str = function.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse function arguments: {arguments_str}")
            return None

        return function_name, arguments

    return None


def build_function_schemas() -> list[dict[str, Any]]:
    """
    Build function schemas for LLM tools.

    Returns:
        List of function schemas
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "record_plan",
                "description": "Record a multi-step plan before executing commands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "string",
                            "description": "The plan to execute",
                        }
                    },
                    "required": ["plan"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "select_task",
                "description": "Select an existing or pending task to edit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": 'Task target (e.g., "existing:123" or "pending:1")',
                        }
                    },
                    "required": ["target"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_task",
                "description": "Stage a brand new task creation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Task title (required)",
                        },
                        "description": {"type": "string", "description": "Task description"},
                        "notes": {"type": "string", "description": "Task notes"},
                        "status": {
                            "type": "string",
                            "enum": ["todo", "in_progress", "done"],
                            "description": "Task status",
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "critical"],
                            "description": "Task urgency",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Due date (YYYY-MM-DD format)",
                        },
                        "deferred_until": {
                            "type": "string",
                            "description": "Deferred until date (YYYY-MM-DD format)",
                        },
                        "recurrence": {
                            "type": "string",
                            "enum": ["none", "daily", "weekly", "monthly", "yearly"],
                            "description": "Recurrence pattern",
                        },
                        "assignee_id": {
                            "type": "integer",
                            "description": "Assigned user ID",
                        },
                        "assigned_group_id": {
                            "type": "integer",
                            "description": "Assigned group ID",
                        },
                        "prerequisite_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of prerequisite task IDs",
                        },
                    },
                    "required": ["title"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_task_fields",
                "description": "Update fields of the currently selected task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "description": {"type": "string", "description": "Task description"},
                        "notes": {"type": "string", "description": "Task notes"},
                        "status": {
                            "type": "string",
                            "enum": ["todo", "in_progress", "done"],
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "critical"],
                        },
                        "due_date": {"type": "string"},
                        "deferred_until": {"type": "string"},
                        "recurrence": {
                            "type": "string",
                            "enum": ["none", "daily", "weekly", "monthly", "yearly"],
                        },
                        "assignee_id": {"type": "integer"},
                        "assigned_group_id": {"type": "integer"},
                        "prerequisite_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "complete_task",
                "description": "Mark the currently selected task as complete",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_task",
                "description": "Delete the currently selected task",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "exit_editing",
                "description": "Exit task editing mode and return to awaiting command",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "discard_all",
                "description": "Discard all staged operations and start over",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "complete_session",
                "description": "Commit all staged operations and end session (MUST be final command)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]
