import json
import logging
import os
import shutil
import subprocess
import sys
from zipfile import ZipFile
from typing import Any, Dict, List

import click
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from constants import (
    NEWLINE,
    EXPORT_DIR_EXCLUDES,
    EXPORT_FILE_EXCLUDES,
)
from fragments import (
    EXPORT_README,
    EXPORT_REQUIREMENTS,
)
from pm.collection import Collection

logging.getLogger("blib2to3").setLevel(logging.ERROR)

THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR: str = ""
TEMPLATE_ENV: Environment = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["json"]),
)


def setup_workspace():
    global WORKSPACE_DIR

    if "-workspace" in sys.argv:
        WORKSPACE_DIR = os.path.abspath(sys.argv[-1])
    else:
        WORKSPACE_DIR = os.path.join(THIS_DIR, "scenes")
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    shutil.copyfile(
        os.path.join(THIS_DIR, "client.py"), os.path.join(WORKSPACE_DIR, "client.py")
    )

    shutil.copytree(
        os.path.join(THIS_DIR, "vars"),
        os.path.join(WORKSPACE_DIR, "vars"),
        dirs_exist_ok=True,
    )

    # TODO: DO this in python?
    run_env: Dict[str, str] = dict(os.environ)
    run_env["PMX_WORKSPACE_DIR"] = WORKSPACE_DIR
    subprocess.run(["fish", "./scripts/get_local_env.fish"], cwd=THIS_DIR, env=run_env)
    subprocess.run(
        ["fish", "./scripts/get_smoke_collection.fish"], cwd=THIS_DIR, env=run_env
    )


def post_processing(root_collections: List[Collection]) -> None:
    if root_collections:
        with open(os.path.join(WORKSPACE_DIR, "run.py"), "w") as writer:

            def _recurse_collections(
                coll: Collection, ns_list: Dict[str, Collection]
            ) -> None:
                ns_list[coll.namespace] = coll
                for child in coll.children:
                    if type(child) is Collection:
                        _recurse_collections(child, ns_list)

            namespaces: Dict[str, Collection] = {}
            for root_collection in root_collections:
                _recurse_collections(root_collection, namespaces)

            render_args: Dict[str, str] = {
                "import_strings": NEWLINE.join(
                    [
                        f"from {ns}.scenarios import tous as {ns.replace('.', '_')}"
                        for ns in namespaces.keys()
                        if len(namespaces[ns].requests) > 0
                    ]
                ),
                "import_fns": ", ".join(
                    [
                        f"{ns.replace('.', '_')}"
                        for ns in namespaces.keys()
                        if len(namespaces[ns].requests) > 0
                    ]
                ),
            }
            template: Template = TEMPLATE_ENV.get_template("run.py.tmpl")
            writer.write(template.render(**render_args))


def extract_env(input_vars: List[Dict[str, str]]) -> Dict[str, str]:
    result = {}
    for pair in input_vars:
        result[pair.get("key", "")] = pair.get("value", "")
    return result


@click.group()
def cli():
    pass


@click.command()
def export():
    """Export postman data to python"""
    setup_workspace()

    with open(os.path.join(WORKSPACE_DIR, "collection.json"), "r") as reader:
        raw: Dict[str, Any] = json.load(reader).get("collection", {})

        env: Dict[str, str] = extract_env(raw.get("variable", []))
        with open(os.path.join(WORKSPACE_DIR, "vars", "global_vars.py"), "w") as writer:
            writer.write(
                f"""GLOBAL_VARS = {json.dumps(env, indent="    ", separators=(",", ":"), sort_keys=True)}"""
            )

        root_collections: List[Collection] = []
        for item in raw.get("item", []):
            root_collection: Collection = Collection(
                item, WORKSPACE_DIR, WORKSPACE_DIR, [], TEMPLATE_ENV
            )
            root_collection.write_scenario()
            root_collections.append(root_collection)

        post_processing(root_collections)


@click.command()
@click.option("-d", "--dir", default="./scenes", help="Directory to archive")
def archive():
    """Make a ready-to-run  archive for sharing"""
    export_arg_index: int = sys.argv.index("-export")
    if len(sys.argv) == (export_arg_index - 1):
        export_dir: str = os.path.abspath("./scenes")
    else:
        export_dir: str = os.path.abspath(sys.argv[export_arg_index + 1])
    if not os.path.isdir(export_dir):
        print(f"Can't find dir: {export_dir}. bugging out")
        sys.exit(1)

    bn: str = os.path.basename(export_dir)
    with ZipFile(f"{bn}.zip", "w") as ex_zip:
        ex_zip.writestr(os.path.join(bn, "README.md"), EXPORT_README)
        ex_zip.writestr(os.path.join(bn, "requirements.txt"), EXPORT_REQUIREMENTS)

        for root, _, files in os.walk(export_dir):
            for afile in files:
                if all([i not in root for i in EXPORT_DIR_EXCLUDES]):
                    if all([i != afile for i in EXPORT_FILE_EXCLUDES]):
                        fullpath = os.path.join(root, afile)
                        ex_zip.write(
                            fullpath,
                            arcname=fullpath.replace(
                                os.path.dirname(export_dir), str()
                            )[1:],
                        )


cli.add_command(export)
cli.add_command(archive)

if __name__ == "__main__":
    cli()
