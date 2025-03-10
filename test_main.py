import unittest
from unittest.mock import MagicMock, call, patch
from datetime import datetime
from zoneinfo import ZoneInfo

from main import update_calendar

TIMEZONE = "America/Toronto"


class TestStringMethods(unittest.TestCase):
    def test_update_calendar_new_games_only(self):
        """
        2 new games for Friday Night
        1 new league (and game) for Wednesday Night
        Ignore Tuesday 5PM
        """
        ccm_leagues = {
            "Friday Night Mixed": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Joker, The\nSheet: 3"
                },
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Erik, Killmonger\nSheet: 4"
                },
                {
                    # 2023-01-20 21:00
                    "datetime": datetime(2023, 1, 20, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Marvel, Thanos\nSheet: 1"
                }
            ],
            "Wednesday Night Men": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 3, 17, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Luthor, Lex\nSheet: 4"
                }
            ]
        }
        cal_leagues = {
            "Friday Night Mixed": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Joker, The\nSheet: 3"
                }
            ],
            "Tuesday 5PM Social League": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 3, 17, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs General, Zod\nSheet: 6"
                }
            ]
        }

        g_mock = MagicMock()
        update_calendar(g_mock, ccm_leagues, cal_leagues)
        calls = [call.create_cal_match(title="Friday Night Mixed", description="Vader, Darth vs Erik, Killmonger\nSheet: 4", start_time=datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.create_cal_match(title="Friday Night Mixed", description="Vader, Darth vs Marvel, Thanos\nSheet: 1",
                                       start_time=datetime(2023, 1, 20, 21, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.create_cal_match(title="Wednesday Night Men", description="Vader, Darth vs Luthor, Lex\nSheet: 4", start_time=datetime(2023, 1, 3, 17, 0, tzinfo=ZoneInfo(key="America/Toronto")))]
        assert g_mock.mock_calls == calls


    @patch("main.datetime")
    def test_update_calendar_readd_existing_game(self, mock_datetime):
        """
        CCM will still send games for that day even after the game start/end time
        Ensure that we do not re-add those if the current time is past the game start time

        No new games
        Current datetime is 2023-01-06 23:00
        We are sent another game by CCM at 2023-01-06 19:00 which has already happened
        Do not re-add that game
        There are two other games being sent by CCM which are already in the calendar
        No new games should be added, or any other cal changes should be made
        """
        mock_datetime.now.return_value = datetime(2023, 1, 6, 23, 0, tzinfo=ZoneInfo(TIMEZONE))
        ccm_leagues = {
            "Friday Night Mixed": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Joker, The\nSheet: 3"
                },
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Erik, Killmonger\nSheet: 4"
                },
                {
                    # 2023-01-20 21:00
                    "datetime": datetime(2023, 1, 20, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Marvel, Thanos\nSheet: 1"
                }
            ]
        }
        cal_leagues = {
            "Friday Night Mixed": [
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Erik, Killmonger\nSheet: 4"
                },
                {
                    # 2023-01-20 21:00
                    "datetime": datetime(2023, 1, 20, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Vader, Darth vs Marvel, Thanos\nSheet: 1"
                }
            ]
        }

        g_mock = MagicMock()
        update_calendar(g_mock, ccm_leagues, cal_leagues)
        calls = []
        assert g_mock.mock_calls == calls


    @patch("main.datetime")
    def test_update_calendar_rescheduled_games(self, mock_datetime):
        """
        Rescheduled games:
        (1) 2023-01-06 21:00 -> 2023-01-06 19:00
        (4) 2023-01-27 21:00 -> 2023-01-27 19:00
        (5) 2023-02-03 19:00 -> 2023-02-03 21:00
        Expect them to be deleted and recreated
        """
        mock_datetime.now.return_value = datetime(2023, 1, 6, 0, 0, tzinfo=ZoneInfo(TIMEZONE))
        ccm_leagues = {
            "Friday Night Mixed": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Epping, John\nSheet: 3"
                },
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Bottcher, Brendan\nSheet: 4"
                },
                {
                    # 2023-01-20 21:00
                    "datetime": datetime(2023, 1, 20, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Koe, Kevin\nSheet: 1"
                },
                {
                    # 2023-01-27 19:00
                    "datetime": datetime(2023, 1, 27, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Edin, Niklas\nSheet: 2"
                },
                {
                    # 2023-02-03 21:00
                    "datetime": datetime(2023, 2, 3, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Moat, Bruce\nSheet: 4"
                },
            ]
        }
        cal_leagues = {
            "Friday Night Mixed": [
                {
                    # 2023-01-06 21:00
                    "datetime": datetime(2023, 1, 6, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Epping, John\nSheet: 3",
                    "event_id": "1"
                },
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Bottcher, Brendan\nSheet: 4",
                    "event_id": "2"
                },
                {
                    # 2023-01-20 21:00
                    "datetime": datetime(2023, 1, 20, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Koe, Kevin\nSheet: 1",
                    "event_id": "3"
                },
                {
                    # 2023-01-27 21:00
                    "datetime": datetime(2023, 1, 27, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Edin, Niklas\nSheet: 2",
                    "event_id": "4"
                },
                {
                    # 2023-02-03 19:00
                    "datetime": datetime(2023, 2, 3, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Gushue, Brad vs Moat, Bruce\nSheet: 4",
                    "event_id": "5"
                },
            ]
        }

        g_mock = MagicMock()
        update_calendar(g_mock, ccm_leagues, cal_leagues)
        calls = [call.create_cal_match(title="Friday Night Mixed", description="Gushue, Brad vs Epping, John\nSheet: 3", start_time=datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.delete_cal_match(event_id="1", title="Friday Night Mixed", start_time=datetime(
                     2023, 1, 13, 21, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.create_cal_match(title="Friday Night Mixed", description="Gushue, Brad vs Edin, Niklas\nSheet: 2",
                                       start_time=datetime(2023, 1, 27, 19, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.delete_cal_match(event_id="4", title="Friday Night Mixed", start_time=datetime(
                     2023, 2, 3, 21, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.delete_cal_match(event_id="5", title="Friday Night Mixed", start_time=datetime(
                     2023, 2, 3, 21, 0, tzinfo=ZoneInfo(key="America/Toronto"))),
                 call.create_cal_match(title="Friday Night Mixed", description="Gushue, Brad vs Moat, Bruce\nSheet: 4", start_time=datetime(2023, 2, 3, 21, 0, tzinfo=ZoneInfo(key="America/Toronto")))]
        assert g_mock.mock_calls == calls

    def test_update_calendar_update_game_description(self):
        """
        Game description is updated
        """
        ccm_leagues = {
            "Monday Night Open": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Einarson, Kerri vs Homan, Rachel\nSheet: 3"
                },
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Einarson, Kerri vs Lawes, Kaitlyn\nSheet: 4"
                }
            ]
        }
        cal_leagues = {
            "Monday Night Open": [
                {
                    # 2023-01-06 19:00
                    "datetime": datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Einarson, Kerri vs Homan, Rachel\nSheet: 2",
                    "event_id": "1"
                },
                {
                    # 2023-01-13 21:00
                    "datetime": datetime(2023, 1, 13, 21, 0, tzinfo=ZoneInfo(TIMEZONE)),
                    "description": "Einarson, Kerri vs Lawes, Kaitlyn\nSheet: 4",
                    "event_id": "2"
                }
            ]
        }

        g_mock = MagicMock()
        update_calendar(g_mock, ccm_leagues, cal_leagues)
        calls = [call.update_cal_match(event_id="1", title="Monday Night Open", description="Einarson, Kerri vs Homan, Rachel\nSheet: 3",
                                       start_time=datetime(2023, 1, 6, 19, 0, tzinfo=ZoneInfo(key="America/Toronto")))]
        assert g_mock.mock_calls == calls


if __name__ == "__main__":
    unittest.main()
