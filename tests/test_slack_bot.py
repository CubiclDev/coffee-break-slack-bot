import copy
import os

from slack_sdk import WebClient
from freezegun import freeze_time

from slack_bot import __version__
from slack_bot.app import get_chosen_users, handler, is_today_holiday, send_message, remove_chosen_users, get_message

TEST_USERS = [
    'U1',
    'U2',
    'U3',
    'U4',
    'U5',
    'U6',
    'U7',
    'U8',
    'U9',
]


def test_version():
    assert __version__ == '0.1.0'


def test_get_users():
    # when
    user_ids = get_chosen_users(TEST_USERS)

    # then
    assert len(user_ids) == 2
    assert user_ids[0] != user_ids[1]


@freeze_time('2021-01-01')
def test_check_holiday_new_year():
    assert is_today_holiday()


@freeze_time('2021-01-02')
def test_check_holiday_no_holiday():
    assert not is_today_holiday()


@freeze_time('2021-01-02')
def test_handler(mocker):
    # given
    mock_get_all_users = mocker.patch('slack_bot.app.get_all_users', return_value=copy.deepcopy(TEST_USERS))
    mock_token = mocker.patch('slack_bot.app.get_token', return_value='xxx')
    mock_send_message = mocker.patch('slack_bot.app.send_message')

    # when
    handler('', '')

    # then
    mock_get_all_users.assert_called_once()
    mock_token.assert_called_once()
    assert mock_send_message.call_count == 3


def test_send_message(mocker):
    # given
    mock_conversations_open = mocker.patch(
        'slack_sdk.WebClient.conversations_open',
        return_value={'channel': {'id': 'dummy'}}
    )
    mock_chat_postMessage = mocker.patch('slack_sdk.WebClient.chat_postMessage')
    mock_get_user_name = mocker.patch('slack_bot.app.get_user_name', side_effect=['Name1', 'Name2'])

    # when
    send_message(['U1', 'U2'], client=WebClient())

    # then
    mock_conversations_open.assert_called_once()
    mock_chat_postMessage.assert_called_once()
    assert mock_get_user_name.call_count == 2
    assert mock_get_user_name.call_args_list[0].args[0] == 'U1'
    assert mock_get_user_name.call_args_list[1].args[0] == 'U2'
    assert mock_chat_postMessage.call_args_list[0][1]['text'] == \
           'Name1 and Name2, you were selected for a shared coffee break.\n' \
           'Please schedule a meeting of 15-20 minutes this week.\n\n' \
           'Your coffee bot ☕'


def test_get_message_default():
    # when
    message = get_message('Name1', 'Name2')

    # then
    assert message == \
           'Name1 and Name2, you were selected for a shared coffee break.\n' \
           'Please schedule a meeting of 15-20 minutes this week.\n\n' \
           'Your coffee bot ☕'


def test_get_message_en(mocker):
    # given
    mocker.patch.dict(os.environ, {"LANGUAGE": "en"}, clear=True)

    # when
    message = get_message('Name1', 'Name2')

    # then
    assert message == \
           'Name1 and Name2, you were selected for a shared coffee break.\n' \
           'Please schedule a meeting of 15-20 minutes this week.\n\n' \
           'Your coffee bot ☕'


def test_get_message_de(mocker):
    # given
    mocker.patch.dict(os.environ, {"LANGUAGE": "de"}, clear=True)

    # when
    message = get_message('Name1', 'Name2')

    # then
    assert message == \
           'Name1 und Name2, ihr wurdet für einen gemeinsamen Kaffeeklatsch ausgelost.\n' \
           'Bitte sucht euch für diese Woche einen Zeitslot von 15-20 Minuten.\n\n' \
           'Euer Kaffeebot ☕'


def test_get_message_unsupported_language(mocker):
    # given
    mocker.patch.dict(os.environ, {"LANGUAGE": "es"}, clear=True)

    # when
    message = get_message('Name1', 'Name2')

    # then
    assert message == \
           'Name1 and Name2, you were selected for a shared coffee break.\n' \
           'Please schedule a meeting of 15-20 minutes this week.\n\n' \
           'Your coffee bot ☕'


def test_remove_users():
    # given
    user_list = copy.deepcopy(TEST_USERS)
    users_length = len(user_list)

    # when
    remove_chosen_users(['U1', 'U2'], user_list)

    # then
    assert len(user_list) == users_length - 2
    assert user_list == [
        'U3',
        'U4',
        'U5',
        'U6',
        'U7',
        'U8',
        'U9',
    ]
