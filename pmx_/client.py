import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

import requests


def init_logging():
    log_fmt = "%(asctime)-25s %(process)d %(name)-25s [%(levelname)-5s] %(message)s"
    logging.getLogger("urllib3").setLevel(logging.WARN)
    logging.basicConfig(format=log_fmt)

    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("e2e.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_fmt))
    _logger.addHandler(file_handler)
    return _logger


logger = init_logging()


class BoostClient:
    def __init__(self, **kwargs):
        self._namespace: str = "default"
        self.base_url: str = kwargs.get("BOOST_URL", str())
        self.user: str = kwargs.get("BOOST_USER", str())
        self.client_id: str = kwargs.get("CLIENT_ID", str())
        self.client_secret: str = kwargs.get("CLIENT_SECRET", str())
        self.auth_token: Optional[str] = None

        self.save_responses: bool = kwargs.get("save_responses", True)
        self.original_response_dir: str = kwargs.get("response_dir", str())
        if self.save_responses and self.response_dir:
            os.makedirs(self.response_dir, exist_ok=True)

        if not self.base_url:
            raise Exception("Missing client auth info: BOOST_URL")
        if not self.user:
            raise Exception("Missing client auth info: BOOST_USER")

        self.authenticate()

        self.read_headers: Dict[str, str] = {
            "BOOST-USER": self.user,
            "Authorization": f"Bearer {self.auth_token}",
        }
        self.write_headers: Dict[str, str] = dict(self.read_headers)
        self.write_headers["Content-Type"] = "application/vnd.api+json"

    @property
    def namespace(self):
        return self._namespace

    @namespace.setter
    def namespace(self, val):
        self._namespace = val
        if self.save_responses and self.response_dir:
            os.makedirs(self.response_dir, exist_ok=True)

    @property
    def response_dir(self):
        return os.path.join(self.original_response_dir, self.namespace)

    @classmethod
    def sleep(cls, seconds=0.2):
        time.sleep(seconds)
        return

    def authenticate(self) -> None:
        self.sleep()

        if "boostinsurance.io" not in self.base_url:
            self.auth_token = "placeholder-token-for-local-dev"
            return

        url = f"{self.base_url}/auth/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        response = requests.post(url, data=data, headers=headers)
        assert response.status_code == 200, response.json()
        self.auth_token = response.json()["access_token"]

    def post(self, endpoint, payload, greek: str = str()):
        print(f">>> POSTing endpoint: {endpoint} <<<")
        self.sleep()
        response = requests.post(endpoint, json=payload, headers=self.write_headers)
        self._save_response(response, greek)

        return response

    def put(self, endpoint, payload, greek: str = str()):
        print(f">>> PUTing endpoint: {endpoint} <<<")
        self.sleep()
        response = requests.put(endpoint, json=payload, headers=self.write_headers)

        self._save_response(response, greek)
        return response

    def patch(self, endpoint, payload, greek: str = str()):
        print(f">>> PATCHing endpoint: {endpoint} <<<")
        self.sleep()
        response = requests.patch(endpoint, json=payload, headers=self.write_headers)
        self._save_response(response, greek)

        return response

    def get(self, endpoint, greek: str = str()):
        print(f">>> GETing endpoint: {endpoint} <<<")
        self.sleep()
        response = requests.get(endpoint, headers=self.read_headers)
        self._save_response(response, greek)
        if "/documents" in endpoint:
            threading.Thread(
                target=self.poll,
                name=f"get_docs_{time.time()}",
                args=(
                    endpoint,
                    greek,
                ),
            ).start()

        return response

    def delete(self, endpoint, payload, greek: str = str()):
        print(f">>> DELETEing endpoint: {endpoint} <<<")

        self.sleep()
        if payload:
            response = requests.delete(
                endpoint, json=payload, headers=self.write_headers
            )
        else:
            response = requests.delete(endpoint, headers=self.read_headers)
        self._save_response(response, greek)

        return response

    def poll(self, endpoint, greek: str = str()):
        attempt: int = 0
        limit: int = 15
        while attempt < limit:
            time.sleep(2)
            response = requests.get(endpoint, headers=self.read_headers)
            data = response.json().get("data", [])
            if len(data) > 0:
                counter = 1000
                for item in data:
                    dl_dir = os.path.join(self.response_dir, "docs")
                    os.makedirs(dl_dir, exist_ok=True)
                    dl_path = os.path.join(dl_dir, f"{greek}-{counter}.pdf")
                    dl_uri: str = item.get("attributes", {}).get("file_url", str())
                    if dl_uri.startswith("https"):
                        dl = requests.get(dl_uri)
                        with open(dl_path, "wb") as writer:
                            writer.write(dl.content)
                    counter += 10
                print(f"Completed downloads for endpoint: {endpoint}")
                break
            attempt += 1
        return

    def _save_response(self, response: requests.Response, greek: str):

        if self.save_responses and greek:
            try:
                pretty_json = json.loads(response.text)
            except json.JSONDecodeError:
                pretty_json = {}

            response_filename = f"{greek}.json"
            data: Dict[str, Any] = pretty_json.get("data", {})
            type_hint: str = data.get("type", str()) if type(data) is dict else str()
            if type_hint:
                response_filename = f"{type_hint}-{response_filename}"

            with open(
                os.path.join(self.response_dir, response_filename), "w"
            ) as writer:
                writer.write(json.dumps(pretty_json, indent=4))
