from freezegun import freeze_time

# Assuming the filter_users_based_on_previous_runs function is in the 'main' module
from slack_bot.app import filter_users_based_on_previous_runs

@freeze_time("2023-08-01")
def test_filter_users():
    sample_runs = [
        {'date': '2023-07-01', 'pair': ['user1', 'user2']},
        {'date': '2023-07-01', 'pair': ['user3', 'user4']},
        {'date': '2023-07-02', 'pair': ['user5', 'user6']},
        {'date': '2023-07-02', 'pair': ['user7', 'user8']},
        {'date': '2023-07-03', 'pair': ['user9', 'user1']},
    ]
    users = [f"user{i}" for i in range(1, 10)]
    taking_break = filter_users_based_on_previous_runs(users, sample_runs)

    # haven't had a run within the last 30 days
    assert "user2" in taking_break
    assert "user3" in taking_break
    assert "user4" in taking_break

    # user1 and user9 had a break in the last round, so they skip this round
    assert "user1" not in taking_break
    assert "user9" not in taking_break
