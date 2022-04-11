# -*- coding: utf-8 -*-
import requests
import os


class InvestecAPIClient(object):
    def __init__(self, client_id: str, secret_key: str, api_key: str):
        if not client_id or not secret_key or not api_key:
            raise ValueError("Client, Secret and API Key Needed")
        self.client_id = client_id
        self.secret_key = secret_key
        self.api_key = api_key
        self.session = requests.Session()
        self.token = None
        self.accounts = None

    def get_auth_token(self) -> None:
        headers = {"x-api-key": self.api_key}
        response = requests.post(
            'https://openapi.investec.com/identity/v2/oauth2/token',
            data={
                'grant_type': 'client_credentials',
                'scope': 'accounts'
            },
            headers=headers,
            auth=(self.client_id, self.secret_key)
        )
        self.session.headers = None
        self.session.headers = {
            'Authorization': 'Bearer ' + response.json()["access_token"]
        }
        self.token = response.json()["access_token"]

    def get_accounts(self) -> None:
        try:
            r = self.session.get("https://openapi.investec.com/za/pb/v1/accounts")
            r.raise_for_status()
            self.accounts = r.json()["data"]["accounts"]
            print(self.accounts)
        except requests.exceptions.HTTPError as error:
            print(error)

    def transfer(self, from_account, to_account, amount, from_reference, to_reference) -> None:
        try:
            r = self.session.post(
                "https://openapi.investec.com/za/pb/v1/accounts/transfermultiple",
                data={
                    "AccountId": from_account,
                    "TransferList": [
                        {
                            "BeneficiaryAccountId": to_account,
                            "Amount": amount,
                            "MyReference": from_reference,
                            "TheirReference": to_reference
                        }
                    ]
                }
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as error:
            print(error)


class CarTrackAPIClient(object):
    def __init__(self, username: str, api_key: str):
        if not username or not api_key or not api_key:
            raise ValueError("Username and API Key is needed")
        self.username = username
        self.api_key = api_key
        self.session = requests.Session()
        self.trips = None
        self.distance = 0

    def get_trips(self, registration, from_date, to_date):
        try:
            response = self.session.get(
                "https://fleetapi-za.cartrack.com/rest/get_all_trips",
                params={
                    "reg": registration,
                    "start_ts": from_date,
                    "end_ts": to_date
                },
                auth=(self.username, self.api_key)
            )
            self.trips = response.json()
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            print(error)

    def calculate_distance(self, registration, from_date, to_date):
        self.get_trips(registration, from_date, to_date)
        distance = 0
        for trip in self.trips:
            distance += int(trip["trip_distance"])
        self.distance = distance / 1000.0


def handler(event, context):
    investec = InvestecAPIClient(os.getenv("investec_client_id"),
                                 os.getenv("investec_secret_key"),
                                 os.getenv("investec_api_key"))

    cartrack = CarTrackAPIClient(os.getenv("cartrack_username"),
                                 os.getenv("cartrack_password"))

    cartrack.calculate_distance("DV77FCGP", "2022-03-31", "2022-04-01")

    value = cartrack.distance * float(os.getenv("rate_per_km"))

    investec.transfer(os.getenv("investec_from_account_id"),
                      os.getenv("investec_to_account_id"),
                      value,
                      "CarTrack",
                      "CarTrack")

    return '1'
