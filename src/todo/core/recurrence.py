"""Recurrence utilities."""

from datetime import date

from dateutil.relativedelta import relativedelta

from todo.models.task import TaskRecurrence


def calculate_next_due_date(
    current_due_date: date, recurrence: TaskRecurrence | str
) -> date | None:
    """
    Calculate the next due date based on the recurrence pattern.

    Args:
        current_due_date: The current due date
        recurrence: The recurrence pattern

    Returns:
        The next due date, or None if no recurrence
    """
    if not current_due_date:
        return None

    if isinstance(recurrence, str):
        try:
            recurrence = TaskRecurrence(recurrence)
        except ValueError:
            return None

    if recurrence == TaskRecurrence.DAILY:
        return current_due_date + relativedelta(days=1)
    elif recurrence == TaskRecurrence.WEEKLY:
        return current_due_date + relativedelta(weeks=1)
    elif recurrence == TaskRecurrence.MONTHLY:
        return current_due_date + relativedelta(months=1)
    elif recurrence == TaskRecurrence.YEARLY:
        return current_due_date + relativedelta(years=1)

    return None
