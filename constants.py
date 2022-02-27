import os
from typing import List, Sequence

THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
NEWLINE: str = "\n"
PREFIX: str = "  "
INDENTED: str = f"{NEWLINE}    "
PANDADOC_MESSASGE: str = str()
with open(os.path.join(THIS_DIR, "vars", "pandadoc.json.tmpl"), "r") as reader:
    PANDADOC_MESSASGE = reader.read()

GREEK_LETTERS: List[str] = [
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lamda",
    "mu",
    "nu",
    "xi",
    "omicron",
    "pi",
    "rho",
    "sigma",
    "tau",
    "upsilon",
    "phi",
    "chi",
    "psi",
    "omega",
]
GREEK_LEN: int = len(GREEK_LETTERS)

# export stuff
EXPORT_DIR_EXCLUDES: Sequence[str] = ("__pycache__", "responses", ".git", ".mypy_cache")
EXPORT_FILE_EXCLUDES: Sequence[str] = ("collection.json", "e2e.log", ".DS_Store")
