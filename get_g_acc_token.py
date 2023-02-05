"""
Creates token.json for the main application
Performs OAuth login flow and writes retrieved token to token.json

Requires Google account credentials in g_credentials.json
https://developers.google.com/calendar/api/quickstart/python#authorize_credentials_for_a_desktop_application
"""

from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

G_ACC_SCOPES = ['https://www.googleapis.com/auth/calendar']


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('./token/token.json'):
        creds = Credentials.from_authorized_user_file('./token/token.json', G_ACC_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("Got refreshed token")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'g_credentials.json',
                G_ACC_SCOPES)

            creds = flow.run_local_server(port=0)
            print("Got new token")
        # Save the credentials for the next run
        with open('./token/token.json', 'w') as token:
            token.write(creds.to_json())
    else:
        print("Token is already valid")


if __name__ == '__main__':
    main()
