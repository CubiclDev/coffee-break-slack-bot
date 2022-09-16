import copy
import os

import pytest
from freezegun import freeze_time
from slack_bot import __version__
from slack_bot.app import (
    get_chosen_users,
    get_message,
    handler,
    is_included_user,
    is_today_holiday,
    remove_chosen_users,
    send_message,
)
from slack_sdk import WebClient

TEST_USERS = [
    "U1",
    "U2",
    "U3",
    "U4",
    "U5",
    "U6",
    "U7",
    "U8",
    "U9",
]


def test_version():
    assert __version__ == "0.1.0"


def test_get_users():
    # when
    user_ids = get_chosen_users(TEST_USERS)

    # then
    assert len(user_ids) == 2
    assert user_ids[0] != user_ids[1]


@freeze_time("2021-01-01")
def test_check_holiday_new_year():
    assert is_today_holiday()


@freeze_time("2021-01-02")
def test_check_holiday_no_holiday():
    assert not is_today_holiday()


@freeze_time("2021-01-02")
def test_handler(mocker):
    # given
    mock_get_all_users = mocker.patch(
        "slack_bot.app.get_users", return_value=copy.deepcopy(TEST_USERS)
    )
    mock_token = mocker.patch("slack_bot.app.get_token", return_value="xxx")
    mock_send_message = mocker.patch("slack_bot.app.send_message")

    # when
    handler("", "")

    # then
    mock_get_all_users.assert_called_once()
    mock_token.assert_called_once()
    assert mock_send_message.call_count == 3


def test_send_message(mocker):
    # given
    mock_conversations_open = mocker.patch(
        "slack_sdk.WebClient.conversations_open",
        return_value={"channel": {"id": "dummy"}},
    )
    mock_chat_postMessage = mocker.patch("slack_sdk.WebClient.chat_postMessage")
    mock_get_user_name = mocker.patch(
        "slack_bot.app.get_user_name", side_effect=["Name1", "Name2"]
    )

    # when
    send_message(["U1", "U2"], client=WebClient())

    # then
    mock_conversations_open.assert_called_once()
    mock_chat_postMessage.assert_called_once()
    assert mock_get_user_name.call_count == 2
    assert mock_get_user_name.call_args_list[0].args[0] == "U1"
    assert mock_get_user_name.call_args_list[1].args[0] == "U2"
    assert (
        mock_chat_postMessage.call_args_list[0][1]["text"]
        == "Name1 and Name2, you were selected for a shared coffee break.\n"
        "Please schedule a meeting of 15-20 minutes this week.\n\n"
        "Your coffee bot ☕"
    )


@pytest.mark.parametrize(
    "language,expected_message",
    [
        (
            None,
            "Name1 and Name2, you were selected for a shared coffee break.\n"
            "Please schedule a meeting of 15-20 minutes this week.\n\n"
            "Your coffee bot ☕",
        ),
        (
            "en",
            "Name1 and Name2, you were selected for a shared coffee break.\n"
            "Please schedule a meeting of 15-20 minutes this week.\n\n"
            "Your coffee bot ☕",
        ),
        (
            "not_defined_language",
            "Name1 and Name2, you were selected for a shared coffee break.\n"
            "Please schedule a meeting of 15-20 minutes this week.\n\n"
            "Your coffee bot ☕",
        ),
        (
            "de",
            "Name1 und Name2, ihr wurdet für einen gemeinsamen Kaffeeklatsch ausgelost.\n"
            "Bitte sucht euch für diese Woche einen Zeitslot von 15-20 Minuten.\n\n"
            "Euer Kaffeebot ☕",
        ),
    ],
)
def test_get_message(mocker, language: str, expected_message: str):
    # given
    if language:
        mocker.patch.dict(os.environ, {"LANGUAGE": language}, clear=True)

    # when
    message = get_message("Name1", "Name2")

    # then
    assert message == expected_message


@pytest.mark.parametrize(
    "user,user_info,expected_value",
    [
        (
            "DELETED_USER_ID",
            {
                "user": {
                    "deleted": True,
                    "profile": {"status_emoji": "", "status_expiration": 0},
                }
            },
            False,
        ),
        (
            "HOLIDAY_USER_ID",
            {
                "user": {
                    "deleted": False,
                    "profile": {"status_emoji": ":palm_tree:", "status_expiration": 0},
                }
            },
            False,
        ),
        (
            "HOLIDAY_EXPIRES_EARLY_USER_ID",
            {
                "user": {
                    "deleted": False,
                    "profile": {
                        "status_emoji": ":palm_tree:",
                        "status_expiration": 1662793200,
                    },
                }
            },
            True,
        ),
        (
            "HOLIDAY_EXPIRES_LATE_USER_ID",
            {
                "user": {
                    "deleted": False,
                    "profile": {
                        "status_emoji": ":palm_tree:",
                        "status_expiration": 1662879600,
                    },
                }
            },
            False,
        ),
        (
            "ILL_USER_ID",
            {
                "user": {
                    "deleted": False,
                    "profile": {
                        "status_emoji": ":face_with_thermometer:",
                        "status_expiration": 0,
                    },
                }
            },
            False,
        ),
        (
            "STANDARD_USER_ID",
            {
                "user": {
                    "deleted": False,
                    "profile": {"status_emoji": "", "status_expiration": 0},
                }
            },
            True,
        ),
        (
            "STANDARD_USER_ID_WITH_EMOJI",
            {
                "user": {
                    "deleted": False,
                    "profile": {"status_emoji": ":no_entry:", "status_expiration": 0},
                }
            },
            True,
        ),
    ],
)
@freeze_time("2022-09-09 10:00:00")
def test_is_included_user(mocker, user: str, user_info: dict, expected_value: bool):
    # given
    mocker.patch("slack_sdk.WebClient.users_info", return_value=user_info)

    # when
    is_included = is_included_user(user, client=WebClient())

    # then
    assert is_included is expected_value


def test_remove_users():
    # given
    user_list = copy.deepcopy(TEST_USERS)
    users_length = len(user_list)

    # when
    remove_chosen_users(["U1", "U2"], user_list)

    # then
    assert len(user_list) == users_length - 2
    assert user_list == [
        "U3",
        "U4",
        "U5",
        "U6",
        "U7",
        "U8",
        "U9",
    ]
