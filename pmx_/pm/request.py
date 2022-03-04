from collections import defaultdict
import json
import os
import re
from typing import Any, Dict, List

from jinja2 import Environment, Template

from pmx_.fragments import READ_PAYLOAD_DATA, READ_PAYLOAD_DATA_PANDADOC
from pmx_.pm.base import E2EBase
from pmx_.constants import (
    GREEK_LEN,
    GREEK_LETTERS,
    INDENTED,
    PREFIX,
    NEWLINE,
    PANDADOC_MESSASGE,
)

WRITE_OUT_EVENTS: bool = False


class Request(E2EBase):
    def __init__(
        self: "Request",
        input_dict: Dict[str, Any],
        stack: List[str],
        template_env: Environment,
        data_dir: str = str(),
        level: int = 0,
        count: int = 0,
    ) -> None:
        self.input_dict: Dict[str, Any] = input_dict
        self.level: int = level
        self.count: int = count
        self.stack = stack
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
        self.method: str = self.input_dict.get("request", {}).get("method", "GET")

        self.data_dir: str = data_dir
        self.url: str = (
            self.input_dict.get("request", {})
            .get("url", {})
            .get("raw", "")
            .replace("{{", "{")
            .replace("}}", "}")
        )
        self.payload: str = (
            self.input_dict.get("request", {}).get("body", {}).get("raw", "")
        )
        self._greek: str = str()
        self._boost_user_key: str = str()

        try:
            self.body: Dict[str, Any] = json.loads(self.payload)
        except json.decoder.JSONDecodeError:
            self.body = {}

        self.events: List[Dict[str, Any]] = self.input_dict.get("event", [str()])

        self.template: Template = template_env.get_template("requests.py.tmpl")

        # stuff related to script parsing
        self._doc_id: str = str()
        self._quote_type: str = str()
        self.pre_script_raw: str = str()
        self.pre_script: List[str] = []
        self.pre_script_event_vars: List[str] = []
        self.parse_pre_event()

        self.test_script_raw: str = str()
        self.test_script: List[str] = []
        self.test_script_event_vars: List[str] = []
        self.parse_test_event()

        self.is_pandadoc_req: bool = "pandadoc" in self.normal_name

    def parse_pre_event(self):
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
            self.pre_script_raw = "\n    ".join(self.pre_script)
            self.pre_script_event_vars = self.extract_event_vars(self.pre_script)

            self._doc_id = (
                "cbyMyQhJgYDu9SeU5zTc5n"
                if "pandadoc_document_id" in self.pre_script_raw
                else "iE7DToRRKNnYXp2DWYd458"
            )
            self._quote_type = (
                "endorsement_quote"
                if "endorsement_quote" in self.pre_script_raw
                else "quote"
            )

    def parse_test_event(self):
        test_event: Dict[str, Any] = {}
        try:
            test_event = next(
                filter(
                    lambda i: type(i) is dict and i.get("listen") == "test", self.events
                )
            )
        except StopIteration:
            pass
        if test_event:
            self.test_script = test_event.get("script", {}).get("exec", [str()])
            self.test_script_raw = "\n    ".join(self.test_script)
            self.test_script_event_vars = self.extract_event_vars(self.test_script)

    def __repr__(self) -> str:
        return (
            f"{NEWLINE}{PREFIX * self.level}{{type: Request, name: {self.name},"
            f"method: {self.method}, url: {self.url}, body: {self.body.keys()}}}"
        )

    @property
    def greek(self):
        if not self._greek:
            if self.count >= GREEK_LEN:
                n: int = int(self.count / GREEK_LEN)
                item: str = GREEK_LETTERS[self.count % GREEK_LEN]
                self._greek = "_".join([item for _ in range(n)])
            else:
                self._greek = GREEK_LETTERS[self.count]
        return self._greek

    @property
    def boost_user_key(self):
        if not self._boost_user_key:
            header_list: List[Dict[str, str]] = self.input_dict.get("request", {}).get(
                "header", []
            )
            for item in header_list:
                if item["key"] == "BOOST-USER":
                    self._boost_user_key = (
                        item["value"].replace("{", "").replace("}", "")
                    )
        return self._boost_user_key

    @property
    def read_payload_data(self) -> str:
        result = str()
        if self.method in ["POST", "PATCH", "PUT", "DELETE"]:
            result = READ_PAYLOAD_DATA.format(**{"greek": self.greek})
            if self.is_pandadoc_req:
                result += READ_PAYLOAD_DATA_PANDADOC
        return result

    def write_request(self) -> str:
        self.write_payload()

        render_args: Dict[str, str | bool] = defaultdict(str)
        render_args.update(
            {
                "boost_user_key": self.boost_user_key,
                "doc_id": self._doc_id,
                "furl": self.url,
                "greek": self.greek,
                "is_pandadoc_req": self.is_pandadoc_req,
                "method": self.method,
                "name": self.name,
                "normal_name": self.normal_name,
                "pre_script_event_vars": INDENTED.join(self.pre_script_event_vars),
                "pre_script_raw": self.pre_script_raw,
                "quote_type": self._quote_type,
                "read_payload_data": self.read_payload_data,
                "test_script_raw": self.test_script_raw,
                "test_script_event_vars": INDENTED.join(self.test_script_event_vars),
                "write_out_events": WRITE_OUT_EVENTS,
            }
        )
        return self.template.render(**render_args)

    def write_payload(self):
        if self.method in ["POST", "PATCH", "PUT", "DELETE"]:
            with open(os.path.join(self.data_dir, f"{self.greek}.json"), "w") as writer:
                if "pandadoc_message" in self.payload:
                    writer.write(PANDADOC_MESSASGE)
                else:
                    writer.write(self.payload)

    def extract_event_vars(self, input_list: List) -> List[str]:
        result: List[str] = []
        use_next_literal_val: bool = False
        ignore_next_environment_set: bool = False
        find_open: bool = False
        find_content: List[str] = []
        for line in input_list:
            line = line.split("//")[0]
            if "pm.variables.set" in line or "pm.environment.set" in line:
                if ignore_next_environment_set:
                    ignore_next_environment_set = False
                    continue
                trim = line.split("(")[1]
                trim = trim.split(")")[0]
                key, val = trim.split(", ")
                key = key.replace("\\", "").replace('"', "").strip()
                val = val.replace("\\", "").replace('"', "").strip()

                if "jsonData.data.id);" in line:
                    result.append(f'CLOSET_VARS["{key}"] = json_data.data.id')
                    continue

                if "jsonData.id);" in line:
                    result.append(f'CLOSET_VARS["{key}"] = json_data.id')
                    continue

                if ', jsonData["data"]["id"])' in line:
                    result.append(f'CLOSET_VARS["{key}"] = json_data.data.id')
                    continue

                if "jsonData.included" in line and line.endswith("find("):
                    result.append(f'CLOSET_VARS["{key}"] = ')
                    find_open = True
                    continue

                er_type = (
                    "endorsement_quote_entity_relation"
                    if "endorsement_quote" in line
                    else "policy_entity_relation"
                )
                er_role = (
                    "additional_insured"
                    if "additional_insured" in key or "_ai" in key
                    else "primary_named_insured"
                )

                if "relation" in key:
                    result.append(
                        f'CLOSET_VARS["{key}"] = get_er_id(json_data.included, "{er_type}", "{er_role}")'
                    )
                    continue

                if (
                    "primary_named_insured" in key
                    or "additional_insured" in key
                    or "_ai" in key
                    or "_pni" in key
                ):
                    result.append(
                        f'CLOSET_VARS["{key}"] = get_entity_id(json_data.included, "{er_type}", "{er_role}")'
                    )
                    continue

                if "jsonData.data" in line:
                    parts = line.split("jsonData")
                    # Second half of split minus trailing );
                    result.append(
                        f'CLOSET_VARS["{key}"] = json_data{parts[-1].rstrip(";").rstrip(")")}'
                    )
                    continue
                if use_next_literal_val:
                    if "format(" in line:
                        val = line.split(",")[-1].replace(";", "")[:-1]
                        result.append(f'CLOSET_VARS["{key}"] = {val}')
                    else:
                        result.append(f'CLOSET_VARS["{key}"] = {val}')
                    use_next_literal_val = False
                else:
                    result.append(f'CLOSET_VARS["{key}"] = "{val}"')

            elif "var jsonData" in line:
                result.append("json_data = Prodict(**response.json())")

            elif "pm.response.to.have.status" in line:
                status = line.split("(")[-1][:-2]
                result.append(f"assert response.status_code == {status}")

            elif "pm.expect(jsonData.data).to.have.lengthOf" in line:
                expected_length = int(line.split("(")[-1][:-1].split(")")[0])
                result.append(f"assert len(json_data.data) == {expected_length}")

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
                    stripped = line.strip()
                    if stripped.startswith("let ") and stripped.endswith(
                        "moment().unix()"
                    ):
                        wline = (
                            line.replace("let ", 'CLOSET_VARS["')
                            .replace(" = ", '"] = moment.now()')
                            .replace("moment().unix()", "")
                        )
                        result.append(wline)
                        ignore_next_environment_set = True
                        continue
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
                        use_next_literal_val = True
                    except IndexError:
                        logger.warning(f"bugging out on {line}")

            elif "pm.environment.get" in line and "pm.expect" not in line:
                wline = (
                    line.replace("var ", 'CLOSET_VARS["')
                    .replace("let ", 'CLOSET_VARS["')
                    .replace("pm.environment.get(", "CLOSET_VARS[")
                    .replace(");", "]")
                    .replace(")", "]")
                    .replace(" = ", '"] = ')
                )
                result.append(wline.strip())

            elif "pm.variables.get" in line and "pm.expect" not in line:
                wline = (
                    line.replace("var ", 'CLOSET_VARS["')
                    .replace("let ", 'CLOSET_VARS["')
                    .replace("pm.variables.get(", "CLOSET_VARS[")
                    .replace(");", "]")
                    .replace(")", "]")
                    .replace(" = ", '"] = ')
                )
                result.append(wline.strip())

            elif "setTimeout" in line:
                timeout = int(line.split(",")[-1].rstrip(";").rstrip(")").strip())
                result.append(f"time.sleep({timeout} / 1000)")

            elif find_open:
                if ")" in line:
                    address: str = str()
                    suffix_parts: List[str] = line.split(")")
                    if len(suffix_parts) > 2:
                        address = suffix_parts[1]

                    # TODO: parse the stuff
                    content: str = " ".join(find_content)
                    result[-1] += f"finder(json_data.included, '{content}'){address}"
                    # reset stuff
                    find_open = False
                    find_content = []
                else:
                    find_content.append(line.strip())

        return result
