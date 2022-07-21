import json
import os

import logging
import math
import random

from slack_sdk import WebClient
import datetime
import holidays

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(__event, __context) -> None:
    if is_today_holiday():
        return

    client = WebClient(token=get_token())

    all_users = get_all_users()
    number_of_coffee_breaks = math.ceil(len(all_users) / 4)  # half of the users should have a coffee break

    for _ in range(number_of_coffee_breaks):
        chosen_users = get_chosen_users(all_users)
        send_message(chosen_users, client)
        remove_chosen_users(chosen_users, all_users)


def send_message(users: list[str], client: WebClient) -> None:
    response = client.conversations_open(users=users)
    user_name_1 = get_user_name(users[0], client)
    user_name_2 = get_user_name(users[1], client)
    logger.info(f'Send coffee break message to {user_name_1} and {user_name_2}')

    client.chat_postMessage(
        channel=response['channel']['id'],
        text=f'{user_name_1} and {user_name_2}, you were selected for a shared coffee break.\n'
             'Please schedule a meeting of 15-20 minutes this week.\n\n'
             'Your coffee bot ☕'
    )


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


def get_all_users() -> list:
    return json.loads(os.environ.get("USERS"))


def get_chosen_users(all_users: list[str]) -> list:
    return random.sample(all_users, k=2)


def get_user_name(user_id: str, client: WebClient) -> str:
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["profile"]["real_name"]
    return user_name.split()[0]
