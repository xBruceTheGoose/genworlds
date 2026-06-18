from collections import deque
import fnmatch
from importlib import import_module
import json
import logging
from multiprocessing import Process
import os
import threading
import time

from genworlds.simulation.sockets.client import SimulationSocketClient
from genworlds.simulation.sockets.server import start_thread

logger = logging.getLogger(__name__)


def get_use_case_list():
    path = "use_cases"
    use_cases = [
        dir_name
        for dir_name in os.listdir(path)
        if os.path.isdir(os.path.join(path, dir_name))
    ]

    world_definitions = []
    for use_case in use_cases:
        try:
            file_names = os.listdir(os.path.join(path, use_case, "world_definitions"))
        except FileNotFoundError:
            logger.warning(
                "No such directory: %s",
                os.path.join(path, use_case, "world_definitions"),
            )
            continue

        for file_name in file_names:
            if fnmatch.fnmatch(file_name, "*.yaml"):
                world_definitions.append(
                    {"use_case": use_case, "world_definition": file_name}
                )

    return world_definitions


def write_dict_to_file(dict_obj, filepath):
    with open(filepath, "w") as f:
        f.write(json.dumps(dict_obj))
        f.write("\n")


def start_server_and_simulation(use_case, world_definition, port):
    module_name = f"use_cases.{use_case}.world_setup"
    function_name = "launch_use_case"

    module = import_module(module_name)
    launch_use_case = getattr(module, function_name)

    start_thread(port=port)

    file_path = os.path.join(
        "use_cases",
        use_case,
        "world_definitions",
        world_definition + ".mocked_record.json",
    )
    events = []

    def process_event(event):
        events.append(event)
        write_dict_to_file({"events": events}, file_path)

    websocket_url = f"ws://127.0.0.1:{port}/ws"
    socket_recorder = SimulationSocketClient(
        process_event=process_event,
        url=websocket_url,
    )

    threading.Thread(
        target=socket_recorder.websocket.run_forever,
        name=f"{use_case}/{world_definition} Recorder Thread",
        daemon=True,
    ).start()

    launch_use_case(
        world_definition=world_definition,
        yaml_data_override={
            "world_definition": {"base_args": {"websocket_url": websocket_url}}
        },
    )


def kill_process(p):
    p.terminate()
    p.join()


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


if __name__ == "__main__":
    use_case_list = get_use_case_list()
    logger.info("Use cases: %s", use_case_list)

    port = 10000
    running_processes = []
    parallel_processes = 5
    minutes = 30
    runtime = minutes * 60
    stagger_time = 60

    for chunk in chunks(use_case_list, parallel_processes):
        logger.info("Processing chunk: %s", chunk)
        for use_case_dict in chunk:
            use_case = use_case_dict["use_case"]
            world_definition = use_case_dict["world_definition"]

            p = Process(
                target=start_server_and_simulation,
                kwargs={
                    "use_case": use_case,
                    "world_definition": world_definition,
                    "port": port,
                },
            )
            running_processes.append(p)
            p.start()

            threading.Timer(runtime, kill_process, args=[p]).start()

            port += 1
            time.sleep(stagger_time)

        time.sleep(runtime + parallel_processes * stagger_time)

    while any(p.is_alive() for p in running_processes):
        time.sleep(1)
