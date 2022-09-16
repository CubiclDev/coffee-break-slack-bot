import datetime
import json
import logging
import math
import os
import random

import holidays
from slack_sdk import WebClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ABSENCE_EMOJIS = [":palm_tree:", ":face_with_thermometer:"]


def handler(__event, __context) -> None:
    if is_today_holiday():
        return

    client = WebClient(token=get_token())

    users = get_users(client)
    # half of the users should have a coffee break
    number_of_coffee_breaks = math.ceil(len(users) / 4)

    for _ in range(number_of_coffee_breaks):
        chosen_users = get_chosen_users(users)
        send_message(chosen_users, client)
        remove_chosen_users(chosen_users, users)


def send_message(users: list[str], client: WebClient) -> None:
    response = client.conversations_open(users=users)
    user_name_1 = get_user_name(users[0], client)
    user_name_2 = get_user_name(users[1], client)
    logger.info(f"Send coffee break message to {user_name_1} and {user_name_2}")

    client.chat_postMessage(
        channel=response["channel"]["id"],
        text=get_message(user_name_1, user_name_2)
    )


def get_message(user_name_1: str, user_name_2: str) -> str:
    language = os.environ.get("LANGUAGE", "en")

    if language == "de":
        return f"{user_name_1} und {user_name_2}, ihr wurdet für einen gemeinsamen Kaffeeklatsch ausgelost.\n" \
               "Bitte sucht euch für diese Woche einen Zeitslot von 15-20 Minuten.\n\n" \
               "Euer Kaffeebot ☕"

    # return english as default
    return f"{user_name_1} and {user_name_2}, you were selected for a shared coffee break.\n" \
           "Please schedule a meeting of 15-20 minutes this week.\n\n" \
           "Your coffee bot ☕"


def remove_chosen_users(chosen_users: list[str], all_users: list[str]):
    all_users.remove(chosen_users[0])
    all_users.remove(chosen_users[1])


def is_today_holiday() -> bool:
    now = datetime.datetime.now()
    de_holidays = holidays.DE()
    holiday = de_holidays.get(now)
    return holiday is not None


def get_token() -> str:
    return os.environ["SLACK_TOKEN"]


def get_users(client: WebClient) -> list:
    users = json.loads(os.environ.get("USERS"))
    return filter_users(users, client)


def filter_users(users: list[str], client: WebClient) -> list[str]:
    filtered_users = filter(lambda user: is_included_user(user, client), users)
    return list(filtered_users)


def is_included_user(user: str, client: WebClient) -> bool:
    user_info = client.users_info(user=user)["user"]
    if user_info["deleted"]:
        return False
    if user_info["profile"]["status_emoji"] not in ABSENCE_EMOJIS:
        return True

    status_expiration = user_info["profile"]["status_expiration"]
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    if status_expiration != 0 and status_expiration < tomorrow.timestamp():
        return True

    return False


def get_chosen_users(all_users: list[str]) -> list:
    return random.sample(all_users, k=2)


def get_user_name(user_id: str, client: WebClient) -> str:
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["profile"]["real_name"]
    return user_name.split()[0]
