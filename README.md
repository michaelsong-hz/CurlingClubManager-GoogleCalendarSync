# CurlingClubManager Google Calendar Sync
This application automatically syncs your upcoming games from CCM to your Google Calendar. You can check if your curling club uses CCM to manage your games by scrolling to the bottom of the page where it will state if it's managed by CCM in the footer.

## Setup

Copy `config_example.json` to `config.json` and fill it in accordingly

Generate `g_credentials.json` from here:
https://developers.google.com/calendar/api/quickstart/python#authorize_credentials_for_a_desktop_application

To generate your Google OAuth token in `./token/token.json`, run
```
pipenv install
pipenv shell

python get_g_acc_token.py
```

## Running the application
Run
```
docker-compose up
```
to bring up the application. By default, it will sync every 6 hours. You can edit the frequency in the `crontab`.
