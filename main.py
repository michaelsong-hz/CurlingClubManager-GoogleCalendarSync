from os import path
from datetime import datetime, timedelta
from json import load
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

G_ACC_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class Google():
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
                # TODO: Report an error
                print("Credentials aren't valid - rerun get_c_acc_token.py")
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
            return dict()

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

    def create_cal_match(self, title: str, description: str, start_time: datetime):
        event = self._generate_cal_event(title, description, start_time)
        self.service.events().insert(
            calendarId=self.config["g_cal_id"], body=event).execute()
        print("Inserted {}".format(start_time.isoformat()))

    def delete_cal_match(self, event_id: str, start_time: datetime):
        self.service.events().delete(
            calendarId=self.config["g_cal_id"], eventId=event_id).execute()
        print("Deleted {}".format(start_time.isoformat()))

    def update_cal_match(self, event_id: str, title: str, description: str, start_time: datetime):
        event = self._generate_cal_event(title, description, start_time)
        self.service.events().update(calendarId=self.config["g_cal_id"],
                                     eventId=event_id, body=event).execute()
        print("Updated {}".format(start_time.isoformat()))


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
        config["ccm_url"] + "index.php/member-s-home/league-information/teams-schedules-standings?view=tss", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    for league_row in soup.find("table").find_all("tr"):
        league = league_row.find("td", valign="top").string.strip()
        if league in ccm_leagues:
            team_href = league_row.find("a", text="Teams")
            if team_href:
                team_response = session.get(
                    config["ccm_url"] + team_href["href"][1:], headers=headers)
                team_soup = BeautifulSoup(team_response.text, "html.parser")
                fill_ccm_team(team_soup, ccm_leagues[league])


def convert_ccm_matches(league_tables):
    leagues = dict()
    for league in league_tables.find_all("table"):
        league_name = ""
        for i, match in enumerate(league.find_all("tr")):
            if i == 0:
                league_name = match.td.string.strip()
                leagues[league_name] = []
            else:
                match_date = ""
                match_time = ""
                match_matchup = ""
                match_sheet = ""
                for j, row in enumerate(match.find_all("td")):
                    match j:
                        case 1:
                            match_date = row.string.strip()
                        case 2:
                            match_time = row.string.strip()
                        case 3:
                            match_matchup = row.string.strip()
                        case 4:
                            match_sheet = row.string.strip()
                        case _:
                            # Row 0 contains nothing
                            pass

                # Pad hour with 0
                if len(match_time) == 7:
                    match_time = "0" + match_time
                match_datetime = datetime.strptime(
                    match_date + " " + match_time, "%m/%d/%Y %I:%M %p")
                match_datetime = match_datetime.replace(
                    tzinfo=ZoneInfo("America/Toronto"))

                leagues[league_name].append({
                    "datetime": match_datetime,
                    "description": "{}\n{}".format(match_matchup, match_sheet),
                    "skips": match_matchup.split(" vs ")
                })
    return leagues


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
    for input_form in soup.find("form", id="login-form").find_all("input", type="hidden"):
        try:
            if input_form["name"] == "return":
                request_body_return = input_form["name"]
            elif input_form["name"] != "option" and input_form["name"] != "task" and input_form["value"] == "1":
                request_body_final_value = input_form["name"]
        except KeyError as e:
            print("Error finding key in input form: {}".format(e))

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
        config["ccm_url"] + "index.php/member-s-home/member-information/my-next-games", headers=headers)
    if response.status_code != 200:
        # TODO: report error
        print("big sad")

    soup = BeautifulSoup(response.text, "html.parser")
    for post in soup.find_all("div", class_="post_intro"):
        try:
            if post.find("h2", itemprop="name").a.string.strip() == "My Next Games":
                ccm_leagues = convert_ccm_matches(post)
                if ccm_leagues:
                    fill_ccm_teams(session, headers, config, ccm_leagues)
                return ccm_leagues
        except AttributeError as e:
            print("Error finding attribute in post: {}".format(e))


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
                        event_id=cal_match["event_id"], start_time=ccm_match["datetime"])
                    cal_index += 1
                elif ccm_date < cal_date:
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
                    event_id=cal_match["event_id"], start_time=ccm_match["datetime"])
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


def main():
    config = load(open("config.json"))
    google = Google(config)
    ccm_leagues = get_ccm_matches(config) or dict()
    if ccm_leagues:
        cal_leagues = google.get_cal_matches()
        update_calendar(google, ccm_leagues, cal_leagues)
        print("{} Calendar sync successful".format(datetime.now().isoformat()))
    else:
        print("{} No upcoming matches found - skipped calendar sync".format(datetime.now().isoformat()))


if __name__ == "__main__":
    main()
