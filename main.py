import json
import logging
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from pm.scenario import Scenario

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger("e2e")


THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
NEWLINE: str = "\n"
PREFIX: str = "  "
INDENTED: str = f"{NEWLINE}    "
WORKSPACE_DIR: str = ""
WRITE_OUT_EVENTS: bool = False


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

    with open(os.path.join(WORKSPACE_DIR, "run.py"), "w") as writer:
        writer.write(
            """\
import os
from vars import SafeArgs, load_vars


THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
NEWLINE: str = "\\n"
PREFIX: str = "  "
ENV: str = "local"
ALL_THE_VARS: SafeArgs = load_vars(os.path.join(THIS_DIR, "vars", f"env.{ENV}.json"))
"""
        )
    with open(os.path.join(THIS_DIR, "vars", "pandadoc.json.tmpl"), "r") as reader:
        PANDADOC_MESSASGE = reader.read()


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

        _ = """
        other_vars: Dict[str, str] = extract_event_vars(
            raw.get("event", [{}])[0].get("script", {}).get("exec", [])
        )
        ALL_THE_VARS.update(other_vars)
        """

        for item in raw.get("item", []):
            Scenario(item, WORKSPACE_DIR, WORKSPACE_DIR, [])


if __name__ == "__main__":
    main()
