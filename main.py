import json
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from vars import SafeArgs, load_vars  # type: ignore

from constants import GREEK_LETTERS, GREEK_LEN  # type: ignore

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger("e2e")


THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
NEWLINE: str = "\n"
PREFIX: str = "  "
INDENTED: str = f"{NEWLINE}    "
WORKSPACE_DIR: str = ""


class E2EBase:
    pass


class Request(E2EBase):
    def __init__(
        self: "Request",
        input_dict: Dict[str, Any],
        stack: List[str],
        data_dir: str = str(),
        level: int = 0,
        count: int = 0,
    ) -> None:
        self.level: int = level
        self.stack = stack
        self.name: Optional[str] = input_dict.get("name")
        self.normal_name: str = (
            self.name.lower()
            .replace(" ", "_")
            .replace("(", "_")
            .replace(")", "_")
            .replace("-", "_")
        )
        self.method: str = input_dict.get("request", {}).get("method", "GET")

        self.data_dir: str = data_dir
        self.url: str = (
            input_dict.get("request", {})
            .get("url", {})
            .get("raw", "")
            .replace("{{", "{")
            .replace("}}", "}")
        )
        self.payload: str = (
            input_dict.get("request", {})
            .get("body", {})
            .get("raw", "")
            .replace("{{", "[[")
            .replace("}}", "]]")
            .replace("{", "^^^")
            .replace("}", "###")
            .replace("[[", "{")
            .replace("]]", "}")
            .replace("^^^", "{{")
            .replace("###", "}}")
        )
        self.greek: str = str()
        if count >= GREEK_LEN:
            n: int = int(count / GREEK_LEN)
            item: str = GREEK_LETTERS[count % GREEK_LEN]
            self.greek = "_".join([item for _ in range(n)])
        else:
            self.greek = GREEK_LETTERS[count]

        try:
            self.body: Dict[str, Any] = json.loads(self.payload)
        except json.decoder.JSONDecodeError:
            self.body = {}

        self.pre_script_raw: str = str()
        self.pre_script: List[str] = []
        self.pre_script_event_vars: List[str] = []

        self.test_script_raw: str = str()
        self.test_script: List[str] = []
        self.test_script_event_vars: List[str] = []

        events: List[Dict[str, Any]] = input_dict.get("event", [str()])

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
            self.pre_script_raw = "\n    ".join(self.pre_script)
            self.pre_script_event_vars = self.extract_event_vars(self.pre_script)

        test_event: Dict[str, Any] = {}
        try:
            test_event = next(
                filter(lambda i: type(i) is dict and i.get("listen") == "test", events)
            )
        except StopIteration:
            pass
        if test_event:
            self.test_script = test_event.get("script", {}).get("exec", [str()])
            self.test_script_raw = "\n    ".join(self.test_script)
            self.test_script_event_vars = self.extract_event_vars(self.test_script)

        self.boost_user_key: str = str()
        header_list: List[Dict[str, str]] = input_dict.get("request", {}).get(
            "header", []
        )
        for item in header_list:
            if item["key"] == "BOOST-USER":
                self.boost_user_key = item["value"].replace("{", "").replace("}", "")

    def __repr__(self) -> str:
        return (
            f"{NEWLINE}{PREFIX * self.level}{{type: Request, name: {self.name},"
            f"method: {self.method}, url: {self.url}, body: {self.body.keys()}}}"
        )

    def write_request(self, writer) -> None:
        furl: str = self.url
        payload: Optional[str] = None
        if self.method in ["POST", "PATCH", "PUT", "DELETE"]:
            payload = f"""\
    payload = str()
    with open(os.path.join(THIS_DIR, "data", "{self.greek}.json"), "r") as reader:
        payload = json.loads(reader.read().format_map(CLOSET_VARS))
"""
        writer.write(
            f"""def {self.normal_name}_{self.greek}():
    print("*** Beginning request: {self.normal_name}_{self.greek} ***")
    \"\"\" {self.method} - {self.name} \"\"\"
    \"\"\" {self.pre_script_raw} \"\"\"
    {INDENTED.join(self.pre_script_event_vars)}
{f"{NEWLINE}{payload}{NEWLINE}    " if payload else "    "}response = getattr(CLIENT, "{self.method.lower()}")(
        "{furl}".format_map(CLOSET_VARS),{NEWLINE if payload else str()}{"        json=payload," if payload else str()}
    )

    \"\"\" {self.test_script_raw} \"\"\"
    print("*** Verifying: {self.normal_name}_{self.greek} results ***")
    print(str())
    {INDENTED.join(self.test_script_event_vars)}


"""
        )
        if self.method in ["POST", "PATCH", "PUT", "DELETE"]:
            with open(os.path.join(self.data_dir, f"{self.greek}.json"), "w") as writer:
                writer.write(self.payload)

    def extract_event_vars(self, input_list: List) -> List[str]:
        result: List[str] = []
        useNextLiteralVal: bool = False
        for line in input_list:
            if "pm.variables.set" in line or "pm.environment.set" in line:
                trim = line.split("(")[1]
                trim = trim.split(")")[0]
                key, val = trim.split(", ")
                key = key.replace("\\", "").replace('"', "").strip()
                val = val.replace("\\", "").replace('"', "").strip()
                if "additional_insured_id" in key:
                    result.append(
                        f'CLOSET_VARS["{key}"] = get_er_id(json_data.included, "additional_insured")'
                    )
                    continue

                if "primary_named_insured_id" in key:
                    result.append(
                        f'CLOSET_VARS["{key}"] = get_er_id(json_data.included, "primary_named_insured")'
                    )
                    continue

                if "jsonData.data" in line:
                    parts = line.split("jsonData")
                    # Second half of split minus trailing );
                    result.append(f'CLOSET_VARS["{key}"] = json_data{parts[-1][:-2]}')
                    continue
                if useNextLiteralVal:
                    if "format(" in line:
                        val = line.split(",")[-1].replace(";", "")[:-1]
                        result.append(f'CLOSET_VARS["{key}"] = {val}')
                    else:
                        result.append(f'CLOSET_VARS["{key}"] = {val}')
                    useNextLiteralVal = False
                else:
                    result.append(f'CLOSET_VARS["{key}"] = "{val}"')

            elif "var jsonData" in line:
                result.append("json_data = Prodict(**response.json())")

            elif "pm.response.to.have.status" in line:
                status = line.split("(")[-1][:-2]
                result.append(f"assert response.status_code == {status}")

            elif "pm.expect(jsonData" in line:
                if (
                    "pm.expect(jsonData.data.attributes.status_reasons).to.eql([]);"
                    in line
                ):
                    result.append(
                        "assert json_data.data.attributes.status_reasons == []"
                    )
                else:
                    k = re.compile(
                        r'[\s]+pm\.expect\(jsonData\.([^\)]+)\)\.to\.eql\([\'"]([a-z]+)[\'"]\)\;'
                    )
                    match = k.match(line)
                    if match:
                        groups = match.groups()
                        result.append(f'assert json_data.{groups[0]} == "{groups[1]}"')

            elif "moment()" in line:
                if "unix()" in line:
                    result.append("moment.now()")
                else:
                    try:
                        norm1 = line[4:-1].replace("moment()", "moment.now()")
                        parts = norm1.split("(")
                        end_parts = (
                            parts[-1][:-1].replace("'", "").replace('"', "").split(",")
                        )
                        prefix = "(".join(parts[:-1])
                        suffix = f"({end_parts[1].strip()}={end_parts[0].strip()})"
                        result.append(f"{prefix}{suffix}")
                        useNextLiteralVal = True
                    except IndexError:
                        logger.warning(f"bugging out on {line}")

        return result


class Scenario(E2EBase):
    def __init__(
        self: "Scenario",
        input_dict: Dict[str, Any],
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
sys.path.insert(0, "{WORKSPACE_DIR}")  # do better

import moment
from prodict import Prodict

from client import BoostClient
from vars import get_er_id, load_vars
{NEWLINE.join(var_imports)}

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger("e2e")

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
                    Scenario(item, self.scenario_dir, self.stack, level=self.level + 1)
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
                    logger.warning(f"Error parsing scenario event: {err}: {line}")

        return result


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
            Scenario(item, WORKSPACE_DIR, [])


if __name__ == "__main__":
    main()
