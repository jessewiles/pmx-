import json
import logging
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from constants import NEWLINE
from pm.request import Request
from pm.scenario import Scenario

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger("e2e")


THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR: str = ""


def setup_workspace():
    global WORKSPACE_DIR

    WORKSPACE_DIR = os.path.join(THIS_DIR, "scenes")
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    shutil.copyfile(
        os.path.join(THIS_DIR, "client.py"), os.path.join(WORKSPACE_DIR, "client.py")
    )

    shutil.copytree(os.path.join(THIS_DIR, "vars"), os.path.join(WORKSPACE_DIR, "vars"))

    # TODO: DO this in python?
    subprocess.run(["fish", "./scripts/get_local_env.fish"], cwd=THIS_DIR)
    subprocess.run(["fish", "./scripts/get_smoke_collection.fish"], cwd=THIS_DIR)


def post_processing(root_scenario: Scenario) -> None:
    with open(os.path.join(WORKSPACE_DIR, "run.py"), "w") as writer:

        def _recurse_scenarios(a_scenario: Scenario, ns_list: Dict[str, bool]) -> None:
            ns_list[a_scenario.namespace] = True
            for child in a_scenario.children:
                if type(child) is Scenario:
                    _recurse_scenarios(child, ns_list)

        namespaces: Dict[str, bool] = {}
        _recurse_scenarios(root_scenario, namespaces)

        import_strings: List[str] = [
            f"from {ns}.scenario import tous as {ns.replace('.', '_')}"
            for ns in namespaces.keys()
        ]
        import_fns: List[str] = [f"{ns.replace('.', '_')}" for ns in namespaces.keys()]

        writer.write(
            f"""\
import os
from concurrent import futures

{NEWLINE.join(import_strings)}

if __name__ == "__main__":
    with futures.ThreadPoolExecutor(max_workers=2) as executor:
        tasks = [executor.submit(job) for job in ({', '.join(import_fns)})]
        for f in futures.as_completed(tasks):
            print("A thing is done")
"""
        )


def extract_env(input_vars: List[Dict[str, str]]) -> Dict[str, str]:
    result = {}
    for pair in input_vars:
        result[pair.get("key", "")] = pair.get("value", "")
    return result


def main():
    setup_workspace()

    with open(os.path.join(WORKSPACE_DIR, "collection.json"), "r") as reader:
        raw: Dict[str, Any] = json.load(reader).get("collection", {})

        env: Dict[str, str] = extract_env(raw.get("variable", []))
        with open(os.path.join(WORKSPACE_DIR, "vars", "global_vars.py"), "w") as writer:
            writer.write(
                f"""\
GLOBAL_VARS = {json.dumps(env, indent="    ", separators=(",", ":"), sort_keys=True)}
"""
            )

        for item in raw.get("item", []):
            root_scenario = Scenario(item, WORKSPACE_DIR, WORKSPACE_DIR, [])

        post_processing(root_scenario)


if __name__ == "__main__":
    main()
