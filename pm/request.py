import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

from pm.base import E2EBase
from constants import (
    GREEK_LEN,
    GREEK_LETTERS,
    PREFIX,
    INDENTED,
    NEWLINE,
    PANDADOC_MESSASGE,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger("e2e")

WRITE_OUT_EVENTS: bool = False


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
        self.payload: str = input_dict.get("request", {}).get("body", {}).get("raw", "")
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

        self.is_pandadoc_req: bool = "pandadoc" in self.normal_name

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
    template = TEMPLATE_ENV.get_template("{self.greek}.json")
    content = template.render(**CLOSET_VARS)
    if content:
        payload = json.loads(content)
"""
            if self.is_pandadoc_req:
                payload += """\
    CLOSET_VARS["pandadoc_signature"] = get_pandadoc_signature(
        CLOSET_VARS["pandadoc_webhook_key"], json.dumps(payload)
    )
"""
        writer.write(
            f"""\
def {self.normal_name}_{self.greek}():
    \"\"\" {self.method} - {self.name} \"\"\"
    print()
    print("-------------------------------------------")
    print("*** Beginning request: {self.name} ***")
"""
        )
        if WRITE_OUT_EVENTS:
            writer.write(
                f"""\
\"\"\" {self.pre_script_raw} \"\"\"
"""
            )
        if self.is_pandadoc_req:
            doc_id: str = (
                "cbyMyQhJgYDu9SeU5zTc5n"
                if "pandadoc_document_id" in self.pre_script_raw
                else "iE7DToRRKNnYXp2DWYd458"
            )
            quote_type: str = (
                "endorsement_quote"
                if "endorsement_quote" in self.pre_script_raw
                else "quote"
            )
            writer.write(
                f"""
    CLOSET_VARS["quote_type"] = "{quote_type}"
    CLOSET_VARS["document_id"] = "{doc_id}"
"""
            )
        writer.write(
            f"""\
    CLOSET_VARS["BOOST_USER"] = CLOSET_VARS["{self.boost_user_key}"]
    {INDENTED.join(self.pre_script_event_vars)}
{f"{NEWLINE}{payload}{NEWLINE}    " if payload else "    "}response = getattr(CLIENT, "{'poll' if '/documents' in self.url else self.method.lower()}")(
        "{furl}".format_map(CLOSET_VARS),{NEWLINE if payload else str()}{"        payload," if payload else str()} greek="{self.greek}",
    )
"""
        )
        if WRITE_OUT_EVENTS:
            writer.write(
                f"""\
\"\"\" {self.test_script_raw} \"\"\"
"""
            )
        writer.write(
            f"""\
    print("^^^ Verifying: {self.normal_name}_{self.greek} results ^^^") 
    print()
    {INDENTED.join(self.test_script_event_vars)}
    print("-------------------------------------------")
    print()


"""
        )
        if self.method in ["POST", "PATCH", "PUT", "DELETE"]:
            with open(os.path.join(self.data_dir, f"{self.greek}.json"), "w") as writer:
                if "pandadoc_message" in self.payload:
                    writer.write(PANDADOC_MESSASGE)
                else:
                    writer.write(self.payload)

    def extract_event_vars(self, input_list: List) -> List[str]:
        result: List[str] = []
        useNextLiteralVal: bool = False
        for line in input_list:
            line = line.split("//")[0]
            if "pm.variables.set" in line or "pm.environment.set" in line:
                trim = line.split("(")[1]
                trim = trim.split(")")[0]
                key, val = trim.split(", ")
                key = key.replace("\\", "").replace('"', "").strip()
                val = val.replace("\\", "").replace('"', "").strip()

                if "jsonData.data.id);" in line:
                    result.append(f'CLOSET_VARS["{key}"] = json_data.data.id')
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
                        f'CLOSET_VARS["{key}"] = json_data{parts[-1].rstring(";").rstring(")")}'
                    )
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

            elif "pm.environment.get" in line and "pm.expect" not in line:
                wline = (
                    line.replace("var ", 'CLOSET_VARS["')
                    .replace("pm.environment.get(", "CLOSET_VARS[")
                    .replace(");", "]")
                    .replace(" = ", '"] = ')
                )
                result.append(wline.strip())

            elif "pm.variables.get" in line and "pm.expect" not in line:
                wline = (
                    line.replace("var ", 'CLOSET_VARS["')
                    .replace("pm.variables.get(", "CLOSET_VARS[")
                    .replace(");", "]")
                    .replace(" = ", '"] = ')
                )
                result.append(wline.strip())

            elif "setTimeout" in line:
                timeout = int(line.split(",")[-1].rstrip(";").rstrip(")").strip())
                result.append(f"time.sleep({timeout} / 1000)")

        return result
