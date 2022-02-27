EXPORT_REQUIREMENTS = """\
moment==0.12.1
requests==2.27.1
prodict==0.8.18
Jinja2==3.0.3
click==8.0.3
enlighten==1.10.2
"""

EXPORT_README = """\
# e2e project

To run this program, make a virtual environment and install the requirements:

```sh
# The following or whatever other method you might use to make a venv (pipenv, pyenv ,etc)
$ virtualenv _venv
$ source _venv/bin/activate
$ pip install -r requirements.txt
```

Run the e2e tests:

```sh
(_venv) $ python run.py
```

## Prior results

The responses from the last run may be included in the arcive if re-running the tests isn't required.
Check `responses` directories in this hierarchy.

```sh
$ find . -type d -name responses
```
"""

READ_PAYLOAD_DATA = """\
    payload = str()
    template = TEMPLATE_ENV.get_template("{greek}.json")
    content = template.render(**CLOSET_VARS)
    if content:
        payload = json.loads(content)
"""

READ_PAYLOAD_DATA_PANDADOC = """\
    CLOSET_VARS["pandadoc_signature"] = get_pandadoc_signature(
        CLOSET_VARS["pandadoc_webhook_key"], json.dumps(payload)
    )
"""
