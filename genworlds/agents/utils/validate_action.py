import json
import logging
from datetime import datetime
from typing import Tuple, Union

from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)


def validate_action(
    agent_id: str,
    action_schema: str,
    pre_filled_event: dict,
    available_action_schemas: dict,
) -> Union[Tuple[bool, dict], str]:
    """
    Validates a pre-filled event against its JSON schema.

    Returns (is_my_action, trigger_event) on success, or an error string on failure.
    """
    try:
        class_name, event_type = action_schema.split(":", 1)
        trigger_event = {
            "event_type": event_type,
            "sender_id": agent_id,
            "created_at": datetime.now().isoformat(),
        }
        trigger_event.update(pre_filled_event)

        if action_schema not in available_action_schemas:
            return (
                f"Unknown action schema '{action_schema}'. "
                "Please refer to the available action schemas."
            )

        raw_schema = available_action_schemas[action_schema]
        event_schema = json.loads(raw_schema.split("|")[-1])
        validate(trigger_event, event_schema)

        is_my_action = class_name == agent_id
        return is_my_action, trigger_event
    except (ValueError, IndexError):
        return (
            f"Malformed action schema '{action_schema}'. "
            "Expected format: '<entity_id>:<ActionClass>'."
        )
    except ValidationError as e:
        return f"Validation Error in args: {e.message}, pre_filled_event: {pre_filled_event}"
    except Exception as e:
        return f"Error: {e!s}, {type(e).__name__}, pre_filled_event: {pre_filled_event}"
