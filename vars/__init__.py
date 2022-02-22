from collections import defaultdict
import json
import os
from typing import Any, Dict, List

from prodict import Prodict

from .times import read_env_times
from .global_vars import GLOBAL_VARS

THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
ENV: str = "local"


class SafeArgs(defaultdict):
    def __missing__(self, key):
        return f"{{{key}}}"


def load_vars(path: str = os.path.join(THIS_DIR, f"env.{ENV}.json")) -> SafeArgs:
    result: SafeArgs = SafeArgs(str)

    result.update(GLOBAL_VARS)

    # Load up the env
    with open(path, "r") as reader:
        env: "list[Dict[str, Any]]" = json.load(reader)
        for item in env:
            result[item["key"]] = item["value"]

    all_times: Dict[str, Any] = read_env_times()
    result.update(all_times)

    return result


def get_entity_id(
    included: List[Dict[str, Any]],
    type_string: str,
    role_string: str,
) -> str:
    try:
        er = next(
            filter(
                lambda i: i["type"] == type_string
                and i["attributes"]["role"] == role_string,
                included,
            )
        )
    except StopIteration:
        return str()

    er = Prodict(**er)
    return er.relationships.entity.data.id


def get_er_id(
    included: List[Dict[str, Any]],
    type_string: str,
    role_string: str,
) -> str:
    try:
        er = next(
            filter(
                lambda i: i["type"] == type_string
                and i["attributes"]["role"] == role_string,
                included,
            )
        )
    except StopIteration:
        return str()

    return er["id"]
