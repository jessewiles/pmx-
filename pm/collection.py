from collections import defaultdict
import logging
import os
from typing import Any, Dict, List, Optional

import black
from jinja2 import Environment, Template

from constants import INDENTED, NEWLINE, PREFIX
from pm.base import E2EBase
from pm.request import Request

SAVE_RESPONSES = True


class Collection(E2EBase):
    def __init__(
        self: "Collection",
        input_dict: Dict[str, Any],
        workspace_dir: str,
        running_dir: str,
        stack: List[str],
        template_env: Environment,
        level: int = 0,
    ) -> None:
        if input_dict:
            self.input_dict: Dict[str, Any] = input_dict
            self.level: int = level
            self.name: str = self.input_dict.get("name", str())
            self.normal_name: str = (
                self.name.lower()
                .replace(" ", "_")
                .replace("(", "_")
                .replace(")", "_")
                .replace("-", "_")
                .replace("/", "_")
                .replace(",", "")
                .replace(":", "")
                .replace("&", "and")
            )
            # reference passed around to all collections for tracking module depth
            self.stack: List[str] = stack
            self.stack.append(self.normal_name)

            # snapshot module namespace
            self.namespace: str = ".".join(self.stack)

            self.children: List[E2EBase] = []
            self.requests: List[E2EBase] = []

            self.client_id_key: str = str()
            self.client_secret_key: str = str()

            self.workspace_dir: str = workspace_dir
            self.collection_dir: str = os.path.join(running_dir, self.normal_name)  # type: ignore
            os.makedirs(self.collection_dir, exist_ok=True)
            with open(os.path.join(self.collection_dir, "__init__.py"), "w") as writer:
                writer.write(f"# {self.name}")

            self.data_dir: str = os.path.join(self.collection_dir, "data")
            os.makedirs(self.data_dir, exist_ok=True)

            self.base_scenario_path: str = os.path.join(self.collection_dir, "base.py")
            self.scenarios_path: str = os.path.join(self.collection_dir, "scenarios.py")

            self.events: List[Dict[str, Any]] = input_dict.get("event", [str()])

            self.pre_script_raw: str = str()
            self.pre_script_event_vars: List[str] = []
            self.parse_pre_collection_vars()

            self.template_env: Environment = template_env
            self.base_template: Template = self.template_env.get_template(
                "base.py.tmpl"
            )
            self.scenarios_template: Template = self.template_env.get_template(
                "scenarios.py.tmpl"
            )

            # main driver
            self.boost_user_key: str = self.route_items(input_dict)

    def parse_pre_collection_vars(self):
        pre_event: Dict[str, Any] = {}
        try:
            pre_event = next(
                filter(
                    lambda i: type(i) is dict and i.get("listen") == "prerequest",
                    self.events,
                )
            )
        except StopIteration:
            pass
        if pre_event:
            self.pre_script = pre_event.get("script", {}).get("exec", [str()])
            self.pre_script_event_vars = self.extract_event_vars(self.pre_script)
            with open(os.path.join(self.collection_dir, "lvars.py"), "w") as lvwriter:
                lvwriter.write(
                    f"VARS = {{{NEWLINE}{(','+INDENTED).join(self.pre_script_event_vars)}\n}}"
                )
        else:
            with open(os.path.join(self.collection_dir, "lvars.py"), "w") as lvwriter:
                lvwriter.write("""VARS = {}""")

    def write_scenario(self):
        if len(self.requests) > 0:
            render_args: defaultdict = defaultdict(str)

            var_imports: List[str] = []
            running_import_path: str = str()
            named_imports: List[str] = []
            for mod in self.stack:
                var_imports.append(
                    f"from {running_import_path}{mod}.lvars import VARS as {mod}_vars"
                )
                running_import_path += f"{mod}."
                named_imports.append(f"{mod}_vars")
            render_args["var_imports"] = NEWLINE.join(var_imports)

            closet_imports: List[str] = []
            for ni in named_imports:
                closet_imports.append(f"CLOSET_VARS.update({ni})")
            render_args["closet_imports"] = NEWLINE.join(closet_imports)

            render_args["boost_user_key"] = self.boost_user_key
            render_args["pypath_prefix"] = "os.path.dirname(" * (len(self.stack) + 1)
            render_args["pypath_suffix"] = ")" * (len(self.stack) + 1)
            render_args["client_id_key"] = self.client_id_key
            render_args["client_secret_key"] = self.client_secret_key
            render_args["namespace"] = self.namespace
            render_args["save_responses"] = SAVE_RESPONSES
            render_args["requests"] = self.requests
            render_args["scenario_name"] = self.name

            black_mode = black.FileMode(
                target_versions={black.mode.TargetVersion.PY310}, line_length=108
            )
            content: str = self.base_template.render(**render_args)
            with open(self.base_scenario_path, "w") as writer:
                try:
                    content = black.format_str(content, mode=black_mode)
                except Exception:
                    pass
                writer.write(content)

            content = self.scenarios_template.render(**render_args)
            with open(self.scenarios_path, "w") as writer:
                writer.write(content)

        else:
            # TODO? list of dirs to remove?
            pass  # os.remove(self.data_dir)

        # pop here?
        popped: str = self.stack.pop()

    def __repr__(self) -> str:
        return (
            f"{NEWLINE}{PREFIX * self.level}{{type: Collection, name: '{self.name}',"
            f"requests: '{self.requests}'}}"
        )

    def route_items(self: "Collection", items: Dict[str, Any]) -> None:
        # return the BOOST-USER header key from this function for use in rendering
        result: str = "unknown"
        counter: int = 0
        for item in items.get("item", []):
            if item.get("item"):
                scene: Collection = Collection(
                    item,
                    self.workspace_dir,
                    self.collection_dir,
                    self.stack,
                    self.template_env,
                    level=self.level + 1,
                )
                scene.write_scenario()
                self.children.append(scene)

            elif item.get("request"):
                req = Request(
                    item,
                    self.stack,
                    self.template_env,
                    data_dir=self.data_dir,
                    level=self.level + 1,
                    count=counter,
                )
                if result == "unknown" and req.boost_user_key != str():
                    result = req.boost_user_key
                # Don't write authentication steps since the client handles this
                if "auth/oauth2/token" in req.url:
                    data_list: List[Dict[str, str]] = (
                        item.get("request").get("body", {}).get("urlencoded", [])
                    )
                    for item in data_list:
                        if item.get("key") == "client_id":
                            self.client_id_key = (
                                item.get("value")
                                .replace("{", str())
                                .replace("}", str())
                            )
                        elif item.get("key") == "client_secret":
                            self.client_secret_key = (
                                item.get("value")
                                .replace("{", str())
                                .replace("}", str())
                            )

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
                    logging.warning(f"Error parsing collection event: {err}: {line}")

        return result


def extract_env(input_vars: List[Dict[str, str]]) -> Dict[str, str]:
    result = {}
    for pair in input_vars:
        result[pair.get("key", "")] = pair.get("value", "")
    return result
