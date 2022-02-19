import logging
import time
from typing import Dict, Optional

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
        self.base_url: str = kwargs.get("BOOST_URL", str())
        self.user: str = kwargs.get("BOOST_USER", str())
        self.client_id: str = kwargs.get("CLIENT_ID", str())
        self.client_secret: str = kwargs.get("CLIENT_SECRET", str())
        self.auth_token: Optional[str] = None

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

    @classmethod
    def sleep(cls, seconds=0.5):
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

    def post(self, endpoint, json):
        self.sleep()
        response = requests.post(endpoint, json=json, headers=self.write_headers)
        return response

    def put(self, endpoint, json):
        self.sleep()
        response = requests.put(endpoint, json=json, headers=self.write_headers)
        return response

    def patch(self, endpoint, json):
        self.sleep()
        response = requests.patch(endpoint, json=json, headers=self.write_headers)
        return response

    def get(self, endpoint):
        self.sleep()
        response = requests.get(endpoint, headers=self.read_headers)
        return response

    def delete(self, endpoint, json):
        self.sleep()
        response = requests.delete(endpoint, json=json, headers=self.write_headers)
        return response
