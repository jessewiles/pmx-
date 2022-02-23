import logging
import os
from typing import Any, Dict, List, Optional

from constants import THIS_DIR, INDENTED, NEWLINE, PREFIX
from pm.base import E2EBase
from pm.request import Request


class Scenario(E2EBase):
    def __init__(
        self: "Scenario",
        input_dict: Dict[str, Any],
        workspace_dir: str,
        running_dir: str,
        stack: List[str],
        level: int = 0,
    ) -> None:
        if input_dict:
            self.level: int = level
            self.name: Optional[str] = input_dict.get("name")
            self.normal_name: str = (
                self.name.lower()
                .replace(" ", "_")
                .replace("(", "_")
                .replace(")", "_")
                .replace("-", "_")
            )
            self.stack: List[str] = stack
            self.stack.append(self.normal_name)

            self.children: List[E2EBase] = []
            self.requests: List[E2EBase] = []

            self.workspace_dir: str = workspace_dir
            self.scenario_dir: str = os.path.join(running_dir, self.normal_name)  # type: ignore
            os.makedirs(self.scenario_dir, exist_ok=True)
            with open(os.path.join(self.scenario_dir, "__init__.py"), "w") as writer:
                writer.write(f"# {self.name}")

            self.data_dir: str = os.path.join(self.scenario_dir, "data")
            os.makedirs(self.data_dir, exist_ok=True)

            scenario_path: str = os.path.join(self.scenario_dir, "scenario.py")

            events: List[Dict[str, Any]] = input_dict.get("event", [str()])

            self.pre_script_raw: str = str()
            self.pre_script_event_vars: List[str] = []

            pre_event: Dict[str, Any] = {}
            try:
                pre_event = next(
                    filter(
                        lambda i: type(i) is dict and i.get("listen") == "prerequest",
                        events,
                    )
                )
            except StopIteration:
                pass
            if pre_event:
                self.pre_script = pre_event.get("script", {}).get("exec", [str()])
                self.pre_script_event_vars = self.extract_event_vars(self.pre_script)
                with open(os.path.join(self.scenario_dir, "lvars.py"), "w") as lvwriter:
                    lvwriter.write(
                        f"""\
VARS = {{
{(','+INDENTED).join(self.pre_script_event_vars)}
}}
"""
                    )

            # main driver
            boost_user_key: str = self.route_items(input_dict)

            var_imports: List[str] = []
            running_import_path: str = str()
            named_imports: List[str] = []
            for mod in self.stack:
                var_imports.append(
                    f"from {running_import_path}{mod}.lvars import VARS as {mod}_vars"
                )
                running_import_path += f"{mod}."
                named_imports.append(f"{mod}_vars")

            closet_imports: List[str] = []
            for ni in named_imports:
                closet_imports.append(f"CLOSET_VARS.update({ni})")

            if len(self.requests) > 0:
                with open(scenario_path, "w") as writer:
                    writer.write(
                        f"""import json
import logging
import os
import sys
import time
sys.path.insert(0, "{self.workspace_dir}")  # do better

import moment
from prodict import Prodict
from jinja2 import Environment, PackageLoader, select_autoescape

from client import BoostClient
from vars import get_entity_id, get_er_id, get_pandadoc_signature, load_vars
{NEWLINE.join(var_imports)}

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger("e2e")

TEMPLATE_ENV: Environment = Environment(
    loader=PackageLoader("{'.'.join(self.stack)}", package_path="data"),
    autoescape=select_autoescape(["json"]),
)

THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
CLOSET_VARS = dict(load_vars())
{NEWLINE.join(closet_imports)}
CLOSET_VARS["BOOST_USER"] = CLOSET_VARS["{boost_user_key}"]

CLIENT = BoostClient(**CLOSET_VARS)


"""
                    )
                    for req in self.requests:
                        req.write_request(writer)
                    writer.write(
                        """
# Running scenarios stubby
if __name__ == "__main__":
"""
                    )
                    for req in self.requests:
                        writer.write(f"    {req.normal_name}_{req.greek}()\n")
            else:
                # TODO? list of dirs to remove?
                pass  # os.remove(self.data_dir)

            # pop here?
            self.stack.pop()

    def __repr__(self) -> str:
        return (
            f"{NEWLINE}{PREFIX * self.level}{{type: Scenario, name: '{self.name}',"
            f"requests: '{self.requests}'}}"
        )

    def route_items(self: "Scenario", items: Dict[str, Any]) -> None:
        # return the BOOST-USER header key from this function for use in rendering
        result: str = "unknown"
        counter: int = 0
        for item in items.get("item", []):
            if item.get("item"):
                self.children.append(
                    Scenario(
                        item,
                        self.workspace_dir,
                        self.scenario_dir,
                        self.stack,
                        level=self.level + 1,
                    )
                )
            elif item.get("request"):
                req = Request(
                    item,
                    self.stack,
                    data_dir=self.data_dir,
                    level=self.level + 1,
                    count=counter,
                )
                if result == "unknown" and req.boost_user_key != str():
                    result = req.boost_user_key
                # Don't write authentication steps since the client handles this
                if "auth/oauth2/token" in req.url:
                    continue

                self.children.append(req)
                self.requests.append(req)
                counter += 1
            else:
                logging.warning(f"Don't know what to do with item: {item}")

        return result

    def extract_event_vars(self, input_list: List) -> Dict[str, str]:
        result: List[str] = []
        for line in input_list:
            if "pm.variables.set" in line:
                try:
                    trim = line.split("(")[1]
                    trim = trim.split(")")[0]
                    key, val = trim.split(",")
                    key = key.replace("\\", "").replace('"', "").strip()
                    val = val.replace("\\", "").replace('"', "").strip()
                    result.append(f'"{key}": "{val}"')
                except Exception as err:
                    logging.warning(f"Error parsing scenario event: {err}: {line}")

        return result


def extract_env(input_vars: List[Dict[str, str]]) -> Dict[str, str]:
    result = {}
    for pair in input_vars:
        result[pair.get("key", "")] = pair.get("value", "")
    return result
