# CurlingClubManager Google Calendar Sync
This application automatically syncs your upcoming games from curling clubs using [Curling Club Manager](https://curlingclubmanager.com/) to Google Calendar. It also automatically adds information about the team matchup in the event description.

From this:
![Screenshot 2023-02-06 222518](https://user-images.githubusercontent.com/16067442/217140945-ae710c3d-4f28-4494-b2ce-372e75f20879.png)

to this:
![Screenshot 2023-02-06 222216](https://user-images.githubusercontent.com/16067442/217140952-1eac9201-349c-4f6c-8171-6bb3740379e0.png)

You can check if your curling club uses CCM to manage your games by scrolling to the bottom of the page, where it will state if it's managed by CCM in the footer.

## Setup

Copy `config_example.json` to `config.json` and fill it in accordingly. `ha_url` and `ha_token` are used to report the sync status to [Home Assistant](https://www.home-assistant.io/). This functionality can be disabled by leaving those as empty strings.

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
docker-compose up -d
```
to bring up the application. By default, it will sync every 6 hours. You can edit the frequency in the `crontab`.

## [Home Assistant](https://www.home-assistant.io/) Entities Card
![image](https://user-images.githubusercontent.com/16067442/226143551-b698735d-4cf7-4480-8340-ebb26701c282.png)
```
type: entities
title: Curling Calendar Sync
entities:
  - entity: sensor.ccm_sync_status
    name: Status
    icon: hass:none
  - entity: sensor.ccm_sync_status
    name: Update Time
    icon: hass:none
    type: attribute
    attribute: update_time
  - entity: sensor.ccm_sync_status
    name: Message
    icon: hass:none
    type: attribute
    attribute: message
```

## License

CurlingClubManager-CalendarSync is licensed under the GNU General Public License. See `NOTICE.md` and `LICENSE.md` in the root of this repository.

![image](https://www.gnu.org/graphics/gplv3-with-text-136x68.png)

## Contact

You can reach me at <hello@michaelsong.me>.
