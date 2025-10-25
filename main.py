from datetime import datetime, timedelta
from enum import Enum
from json import load
from os import path
from sys import exit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

G_ACC_SCOPES = ["https://www.googleapis.com/auth/calendar"]

class ChangeType(Enum):
    ADDITION = 1
    DELETION = 2
    UPDATE = 3


class Google():
    _sync_changes = {}
    def __init__(self, config):
        self.config = config

        # Create authorized Google account credentials
        creds = None
        # The file token.json stores the user"s access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if path.exists("./token/token.json"):
            creds = Credentials.from_authorized_user_file(
                "./token/token.json", G_ACC_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save the credentials for the next run
                with open("./token/token.json", "w") as token:
                    token.write(creds.to_json())
            else:
                message = "Credentials aren't valid - rerun get_c_acc_token.py"
                print(message)
                update_home_assistant(config, message, success=False)
                exit(1)
        self.service = build(
            "calendar", "v3", credentials=creds)

    def get_cal_matches(self):
        try:
            now = datetime.utcnow().isoformat() + "Z"  # "Z" indicates UTC time
            events_result = self.service.events().list(calendarId=self.config["g_cal_id"], timeMin=now,
                                                       maxResults=50, singleEvents=True,
                                                       orderBy="startTime").execute()
            events = events_result.get("items", [])

        except HttpError as error:
            print("An error occurred: %s" % error)
            update_home_assistant(self.config, "Error retrieving Google calendar", success=False)
            exit(1)

        if not events:
            print("No upcoming events found.")

        leagues = dict()
        for event in events:
            match_datetime = datetime.fromisoformat(
                event["start"].get("dateTime", event["start"].get("date")))
            match_description = ""
            if "description" in event:
                match_description = event["description"]

            if event["summary"] not in leagues:
                leagues[event["summary"]] = []
            leagues[event["summary"]].append({
                "datetime": match_datetime,
                "description": match_description,
                "event_id": event["id"]
            })
        return leagues

    def _generate_cal_event(self, title: str, description: str, start_time: datetime):
        return {
            "summary": title,
            "location": self.config["match_location"],
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "America/Toronto",
            },
            "end": {
                "dateTime": (start_time + timedelta(hours=self.config["match_duration_hours"], minutes=self.config["match_duration_min"])).isoformat(),
                "timeZone": "America/Toronto",
            },
        }

    def _add_sync_change(self, league: str, change_type: ChangeType):
        if league not in self._sync_changes:
            self._sync_changes[league] = {
                ChangeType.ADDITION.name: 0,
                ChangeType.DELETION.name: 0,
                ChangeType.UPDATE.name: 0
            }
        if change_type == ChangeType.ADDITION:
            self._sync_changes[league][ChangeType.ADDITION.name] += 1
        if change_type == ChangeType.DELETION:
            self._sync_changes[league][ChangeType.DELETION.name] += 1
        if change_type == ChangeType.UPDATE:
            self._sync_changes[league][ChangeType.UPDATE.name] += 1

    def create_cal_match(self, title: str, description: str, start_time: datetime):
        event = self._generate_cal_event(title, description, start_time)
        self.service.events().insert(
            calendarId=self.config["g_cal_id"], body=event).execute()
        print("Added {} {}".format(title, start_time.isoformat()))
        self._add_sync_change(title, ChangeType.ADDITION)

    def delete_cal_match(self, event_id: str, title: str, start_time: datetime):
        self.service.events().delete(
            calendarId=self.config["g_cal_id"], eventId=event_id).execute()
        print("Removed {} {}".format(title, start_time.isoformat()))
        self._add_sync_change(title, ChangeType.DELETION)

    def update_cal_match(self, event_id: str, title: str, description: str, start_time: datetime):
        event = self._generate_cal_event(title, description, start_time)
        self.service.events().update(calendarId=self.config["g_cal_id"],
                                     eventId=event_id, body=event).execute()
        print("Updated {} {}".format(title, start_time.isoformat()))
        self._add_sync_change(title, ChangeType.UPDATE)

    def _get_changes_format(self, change_type: ChangeType, num_changes: int) -> str:
        game_string = "games"
        if num_changes == 1:
            game_string = "game"
        change_string = ""
        if change_type == ChangeType.ADDITION:
            change_string = "added"
        elif change_type == ChangeType.DELETION:
            change_string = "deleted"
        elif change_type == ChangeType.UPDATE:
            change_string = "updated"
        return "{} {} {}, ".format(num_changes, game_string, change_string)

    def get_changes(self) -> str:
        sync_changes = ""
        for league in self._sync_changes:
            sync_changes += "{}: ".format(league)
            if self._sync_changes[league][ChangeType.ADDITION.name]:
                sync_changes += self._get_changes_format(ChangeType.ADDITION, self._sync_changes[league][ChangeType.ADDITION.name])
            if self._sync_changes[league][ChangeType.DELETION.name]:
                sync_changes += self._get_changes_format(ChangeType.DELETION, self._sync_changes[league][ChangeType.DELETION.name])
            if self._sync_changes[league][ChangeType.UPDATE.name]:
                sync_changes += self._get_changes_format(ChangeType.UPDATE, self._sync_changes[league][ChangeType.UPDATE.name])
            sync_changes = sync_changes[:-2]
            sync_changes += ". "
        if sync_changes:
            sync_changes = sync_changes[:-1]
        return sync_changes

def fill_ccm_team(soup: BeautifulSoup, ccm_matches: dict):
    teams = dict()
    for team in soup.find("tbody").find_all("tr"):
        index = 0
        skip = ""
        for team_member_row in team.find_all("td"):
            if index == 0:
                pass
            elif index == 1:
                skip = team_member_row.text.strip()
                teams[skip] = [skip]
            else:
                team_member = team_member_row.text.strip()
                if team_member:
                    teams[skip].append(team_member)
            index += 1
    for ccm_match in ccm_matches:
        for skip in ccm_match["skips"]:
            if skip in teams:
                team_description_text = ""
                for team_member in teams[skip]:
                    team_description_text += "\n" + team_member
                ccm_match["description"] += "\n\nTeam {}:{}".format(
                    skip.split(", ")[0], team_description_text)


def fill_ccm_teams(session: requests.Session, headers: dict[str, str], config: dict, ccm_leagues: dict):
    response = session.get(
        config["ccm_url"] + "/index.php/member-s-home/league-information/teams-schedules-standings?view=tss", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    for league_row in soup.find("table").find_all("tr"):
        league = league_row.find("td", valign="top").string.strip()
        if league in ccm_leagues:
            team_href = league_row.find("a", string="Teams")
            if team_href:
                team_response = session.get(
                    config["ccm_url"] + team_href["href"], headers=headers)
                team_soup = BeautifulSoup(team_response.text, "html.parser")
                fill_ccm_team(team_soup, ccm_leagues[league])


def convert_ccm_matches(session, headers, config, leagues, ccm_leagues):
    for league_name in leagues:
        response = session.get(config["ccm_url"] + leagues[league_name]["link"], headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        first_row = True
        for schedule_row in soup.find("table", id="schedule").find_all("tr"):
            if first_row:
                first_row = False
                continue
            i = 0
            for schedule_col in schedule_row.find_all("td"):
                match i:
                    case 1:
                        match_date = schedule_col.text.strip()
                    case 2:
                        match_time = schedule_col.text.strip()
                    case 3:
                        match_sheet = schedule_col.text.strip()
                    case 4:
                        match_opp = schedule_col.text.strip()
                    case 5:
                        match_result = schedule_col.text.strip()
                    case _:
                        pass
                i += 1

            # Pad hour with 0
            if len(match_time) == 7:
                match_time = "0" + match_time
            match_datetime = datetime.strptime(
                match_date + " " + match_time, "%m/%d/%Y %I:%M %p")
            match_datetime = match_datetime.replace(
                tzinfo=ZoneInfo("America/Toronto"))

            ccm_leagues[league_name].append({
                "datetime": match_datetime,
                "description": "{} vs {}\nSheet {}\n{}".format(match_opp, leagues[league_name]["skip"], match_sheet, match_result),
                "skips": [match_opp, leagues[league_name]["skip"]]
            })


def get_header_cookie(cookies: dict):
    for cookie in cookies.keys():
        if len(cookie) == 32:
            return "{}={}".format(cookie, cookies[cookie])


def get_ccm_matches(config: dict):
    # Get initial cookies
    session = requests.Session()
    response = session.get(config["ccm_url"])
    soup = BeautifulSoup(response.text, "html.parser")

    request_body_return = ""
    request_body_final_value = ""
    for input_form in soup.find("form", id="login-form-16").find_all("input", type="hidden"):
        try:
            if input_form["name"] == "return":
                request_body_return = input_form["name"]
            elif input_form["name"] != "option" and input_form["name"] != "task" and input_form["value"] == "1":
                request_body_final_value = input_form["name"]
        except KeyError as e:
            print("Error finding key in input form: {}".format(e))
            update_home_assistant(config, "Error logging in to CCM", success=False)
            exit(1)

    # Login
    request_body = {
        "username": config["ccm_username"],
        "password": config["ccm_password"],
        "Submit": "",
        "option": "com_users",
        "task": "user.login",
        "return": request_body_return,
        request_body_final_value: "1"
    }

    cookie = get_header_cookie(session.cookies.get_dict())
    headers = {"Cookie": cookie}
    response = session.post(config["ccm_url"],
                            headers=headers, data=request_body, allow_redirects=False)

    # Retrieve next games
    cookie = get_header_cookie(session.cookies.get_dict())
    headers = {"Cookie": cookie + "; joomla_user_state=logged_in"}
    response = session.get(
        config["ccm_url"] + "/index.php/component/curling/?view=my_teams", headers=headers)
    if response.status_code != 200:
        update_home_assistant(config, "Invalid CCM credentials", success=False)
        exit(1)

    leagues = {}
    ccm_leagues = {}
    league_names = []
    soup = BeautifulSoup(response.text, "html.parser")
    league_div = None
    for league_name in soup.find("table", id="roster").parent.find_all("h2"):
        if not league_div:
            league_div = league_name.parent
        league_name = league_name.text

        leagues[league_name] = {
            "link": "",
            "skip": "",
        }
        ccm_leagues[league_name] = []
        league_names.append(league_name)
    i = 0
    for post in league_div.find_all("table", id="roster"):
        leagues[league_names[i]]["skip"] = post.find("tbody").find("td").text
        i += 1
    i = 0
    for post in league_div.find_all("a", string="Team Schedule and Results Summary"):
        leagues[league_names[i]]["link"] = post["href"]
        i += 1

    convert_ccm_matches(session, headers, config, leagues, ccm_leagues)
    if ccm_leagues:
        fill_ccm_teams(session, headers, config, ccm_leagues)

    return ccm_leagues


def update_calendar(google: Google, ccm_leagues: dict, cal_leagues: dict):
    for league in ccm_leagues.keys():
        ccm_index = 0
        cal_index = 0
        if league in cal_leagues:
            while ccm_index < len(ccm_leagues[league]) and cal_index < len(cal_leagues[league]):
                ccm_match = ccm_leagues[league][ccm_index]
                cal_match = cal_leagues[league][cal_index]
                ccm_date = ccm_match["datetime"]
                cal_date = cal_match["datetime"]
                if ccm_date == cal_date:
                    # Check description and update if necessary
                    if ccm_match["description"] != cal_match["description"]:
                        google.update_cal_match(
                            event_id=cal_match["event_id"],
                            title=league,
                            description=ccm_match["description"],
                            start_time=ccm_match["datetime"]
                        )
                    ccm_index += 1
                    cal_index += 1
                elif ccm_date > cal_date:
                    # Delete from calendar
                    google.delete_cal_match(
                        event_id=cal_match["event_id"], title=league, start_time=ccm_match["datetime"])
                    cal_index += 1
                elif ccm_date < cal_date:
                    # Only add the game if the game start time is after the current time
                    if ccm_date >= datetime.now(ZoneInfo("America/Toronto")):
                        # Add to calendar
                        google.create_cal_match(
                            title=league,
                            description=ccm_match["description"],
                            start_time=ccm_match["datetime"]
                        )
                    ccm_index += 1

            while len(cal_leagues[league]) > cal_index:
                # Delete excess from calendar
                cal_match = cal_leagues[league][cal_index]
                google.delete_cal_match(
                    event_id=cal_match["event_id"], title=league, start_time=ccm_match["datetime"])
                cal_index += 1
        while len(ccm_leagues[league]) > ccm_index:
            # Add remaining to calendar
            ccm_match = ccm_leagues[league][ccm_index]
            google.create_cal_match(
                title=league,
                description=ccm_match["description"],
                start_time=ccm_match["datetime"]
            )
            ccm_index += 1

def update_home_assistant(config: dict, message: str, success: bool):
    if config["ha_url"]:
        url = config["ha_url"] + "/api/states/sensor.ccm_sync_status"
        headers = {
            "Authorization": "Bearer " + config["ha_token"],
            "content-type": "application/json",
        }

        state = "Failure"
        if success:
            state = "Success"

        request_json = {
            "state": state,
            "attributes": {
                "update_time": datetime.now().isoformat()
            }
        }
        if message:
            request_json["attributes"]["message"] = message

        requests.post(url, headers=headers, json=request_json)

def main():
    config = load(open("config.json"))
    google = Google(config)
    ccm_leagues = get_ccm_matches(config) or dict()
    if ccm_leagues:
        cal_leagues = google.get_cal_matches()
        update_calendar(google, ccm_leagues, cal_leagues)
        print("{} Calendar sync successful".format(datetime.now().isoformat()))
        update_home_assistant(config, google.get_changes(), success=True)
    else:
        print("{} No upcoming matches found - skipped calendar sync".format(datetime.now().isoformat()))
        update_home_assistant(config, "No upcoming matches found - skipped calendar sync", success=True)

if __name__ == "__main__":
    main()
