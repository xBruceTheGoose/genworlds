"""
World setup utilities for loading and launching a simulation from a YAML definition.

Security: the class loader enforces an allowlist of permitted module prefixes —
any class_path that resolves outside the allowlist is rejected to prevent
arbitrary code execution via YAML injection.
"""
from __future__ import annotations

import importlib
import inspect
import logging
import os
import threading
from typing import Any

import yaml
from dotenv import load_dotenv

from genworlds.simulation.simulation import Simulation

logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=".env")

ABS_PATH = os.path.dirname(os.path.abspath(__file__))

# Only allow classes from these package prefixes to be loaded via YAML.
_ALLOWED_MODULE_PREFIXES = (
    "genworlds.",
    "use_cases.",
)


def load_yaml(yaml_path: str) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_class(class_path: str) -> type:
    """
    Import and return a class by dotted path.

    Raises ValueError if the module path is not in the allowlist.
    """
    module_path, class_name = class_path.rsplit(".", 1)
    if not any(module_path.startswith(prefix) for prefix in _ALLOWED_MODULE_PREFIXES):
        raise ValueError(
            f"Refused to load class from untrusted module '{module_path}'. "
            f"Allowed prefixes: {_ALLOWED_MODULE_PREFIXES}"
        )
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _filter_kwargs(cls: type, data: dict) -> dict:
    arg_names = inspect.getfullargspec(cls.__init__).args
    return {k: v for k, v in data.items() if k in arg_names}


def construct_object(object_data: dict, base_kwargs: dict) -> tuple[Any, dict]:
    if not isinstance(object_data, dict):
        raise ValueError("Object data must be a dictionary")
    cls = load_class(object_data["class"])
    world_properties = object_data.pop("world_properties", {})
    obj = cls(**base_kwargs, **_filter_kwargs(cls, object_data))
    return obj, world_properties


def construct_agent(
    agent_data: dict, base_agent_data: dict, base_kwargs: dict
) -> tuple[Any, dict]:
    if not isinstance(agent_data, dict):
        raise ValueError("Agent data must be a dictionary")

    combined: dict = {}
    for k in set(agent_data) | set(base_agent_data):
        a_val = agent_data.get(k)
        b_val = base_agent_data.get(k)
        if a_val is not None and b_val is not None and isinstance(a_val, list):
            combined[k] = b_val + a_val
        elif a_val is not None:
            combined[k] = a_val
        elif b_val is not None:
            combined[k] = b_val

    cls = load_class(combined["class"])
    world_properties = combined.pop("world_properties", {})
    agent = cls(**base_kwargs, **_filter_kwargs(cls, combined))
    return agent, world_properties


def construct_world(data: dict) -> tuple:
    if "world" not in data:
        raise ValueError("Missing 'world' key in world definition data")

    base_kwargs: dict = data.get("base_args", {})
    world_def: dict = data["world"]

    objects = [
        construct_object(obj, base_kwargs) for obj in world_def.get("objects", [])
    ]
    base_agent_data: dict = world_def.get("base_agent", {})
    agents = [
        construct_agent(agent, base_agent_data, base_kwargs)
        for agent in world_def.get("agents", [])
    ]

    cls = load_class(world_def["class"])
    world = cls(**base_kwargs, **_filter_kwargs(cls, world_def))
    locations = world_def.get("locations", [])

    return world, objects, agents, locations


def merge_dicts(d1: dict, d2: dict) -> dict:
    for key, value in d2.items():
        if isinstance(value, dict):
            merge_dicts(d1.setdefault(key, {}), value)
        else:
            d1[key] = value
    return d1


def launch_use_case(
    world_definition: str = "default_world_definition.yaml",
    stop_event: threading.Event = None,
    yaml_data_override: dict = None,
):
    yaml_data = merge_dicts(
        load_yaml(os.path.join(ABS_PATH, "world_definitions", world_definition)),
        yaml_data_override or {},
    )
    logger.debug("World definition: %s", yaml_data)

    world, objects, agents, _locations = construct_world(yaml_data["world_definition"])

    simulation = Simulation(
        name=world.name,
        description=world.description,
        world=world,
        objects=[o for o, _ in objects],
        agents=[a for a, _ in agents],
        stop_event=stop_event,
    )
    simulation.launch()


if __name__ == "__main__":
    launch_use_case()
