from collections import defaultdict
import hashlib
import hmac
import inspect
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import enlighten
from prodict import Prodict  # type: ignore

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


def get_pandadoc_signature(
    key: str,
    body: str,
) -> str:
    return hmac.new(
        key.encode(),
        body.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def get_coverage_by_id(
    included: List[Dict[str, Any]],
    id_to_lookup: str,
) -> Optional[str]:
    try:
        coverage = next(
            filter(
                lambda i: i["type"] == "endorsement_quote_coverage"
                and i["relationships"]["product_coverage"]["data"]["id"]
                == id_to_lookup,
                included,
            )
        )
    except StopIteration:
        return None

    coverage = Prodict(**coverage)
    return coverage.id  # type: ignore


def get_stack_path():
    stack = list(reversed([f.function for f in inspect.stack()]))[1:-3]
    return ".".join(stack)


def finder(included: List[Dict[str, Any]], arrow_func: str) -> Optional[Prodict]:
    def looker(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        def eval_func(item, k, v):
            v = v.replace('"', str())
            lookup = item
            keys = list(reversed(k.split(".")[1:]))
            while keys:
                lookup = lookup.get(keys.pop(), {})
            return lookup == v

        try:
            result = next(
                filter(
                    lambda i: all([eval_func(i, x, y) for x, y in pairs]),
                    included,
                )
            )
        except StopIteration:
            print("stopiteration")
            pass
        return result

    clean: str = arrow_func.split("=> ")[-1]
    parts: List[str] = clean.split("&&")
    exparts: List[Tuple[str, Any]] = []
    for part in parts:
        subparts: List[str] = list(map(lambda i: i.strip(), part.split("==")))
        exparts.append(
            (
                subparts[0],
                subparts[-1],
            )
        )
    expresult = looker(exparts)
    return Prodict(**expresult)


class ProgressBar:
    def __init__(self):
        self.manager: "enlighten.NotebookManager|enlighten.Manager" = (
            enlighten.get_manager(no_resize=True)
        )
        self._counter: Optional[Any | enlighten.Counter] = None
        self._calls: Dict[str, int] = {}
        self._caller: str = str()
        self._completed_work: int = 0
        self._total_work: int = 0

    @property
    def counter(self):
        return self._counter

    @property
    def caller(self):
        return self._caller

    @caller.setter
    def caller(self, val):
        self._caller = val

    @property
    def calls(self):
        return self._calls

    @property
    def completed_work(self):
        return self._completed_work

    @property
    def total_work(self):
        return self._total_work

    @property
    def percent_done(self):
        return f"{int((self.completed_work/self.total_work)*100)}%"

    def init_top_caller(self, function_name: str, desc: str):
        self.caller = function_name
        self._total_work = self.calls[function_name]
        self.make_counter(self.total_work, desc)

    def make_counter(self, total: int, desc: str) -> None:
        self._counter = self.manager.counter(
            total=total, desc=desc, leave=True, color="green"
        )

    def increment_total_work(self):
        self._total_work += 1

    def increment_completed_work(self):
        self._completed_work += 1
