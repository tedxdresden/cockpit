from __future__ import print_function
import httplib2
import os
import random
#  import ipdb
import smtplib
import requests
import time

from datetime import datetime
from slackclient import SlackClient
from os.path import basename
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None


def simple_pass_gen():
    """
    Generates a simple 8 char random password
    """

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    upperalphabet = alphabet.upper()
    pw_len = 8
    pwlist = []

    for i in range(pw_len//3):
        pwlist.append(alphabet[random.randrange(len(alphabet))])
        pwlist.append(upperalphabet[random.randrange(len(upperalphabet))])
        pwlist.append(str(random.randrange(10)))

    for i in range(pw_len-len(pwlist)):
        pwlist.append(alphabet[random.randrange(len(alphabet))])

    random.shuffle(pwlist)
    pwstring = "".join(pwlist)
    return pwstring


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/admin-directory_v1-python-quickstart.json
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.group',
    'https://www.googleapis.com/auth/admin.directory.orgunit'
]

CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Directory API Python Quickstart'

MY_TEDXEMAIL_USERNAME = 'changeme@tedxdresden.com'
MY_TEDXEMAIL_PASSWORD = None

MY_SLACK_TOKEN = None
MY_TRELLO_TOKEN = None
MY_TRELLO_KEY = None

with open('my_tedxdd_email_passwd') as my_tedxdd_email_passwd:
    MY_TEDXEMAIL_PASSWORD = my_tedxdd_email_passwd.readline().replace(
        "\n", "")

with open('my_slack_token') as my_slack_token:
    MY_SLACK_TOKEN = my_slack_token.readline().replace("\n", "")

with open('my_trello_token') as my_trello_token:
    MY_TRELLO_TOKEN = my_trello_token.readline().replace("\n", "")

with open('my_trello_key') as my_trello_key:
    MY_TRELLO_KEY = my_trello_key.readline().replace("\n", "")


class EmailWrapper:
    def __init__(self):
        self.smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        self.login()

    def login(self):
        self.smtp_server.ehlo()
        self.smtp_server.login(MY_TEDXEMAIL_USERNAME, MY_TEDXEMAIL_PASSWORD)

    def logout(self):
        self.smtp_server.quit()

    def send_email(self, to_list, cc_list, subject, body, attachments=[]):
        frm = MY_TEDXEMAIL_USERNAME
        rcpts = to_list + cc_list + [MY_TEDXEMAIL_USERNAME]
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['To'] = str.join(",", to_list)
        msg['Cc'] = str.join(",", cc_list)
        msg['Bcc'] = MY_TEDXEMAIL_USERNAME
        msg.attach(MIMEText(body, 'plain'))

        for attachment in attachments:
            with open(attachment, "rb") as file:
                part = MIMEApplication(
                    file.read(), Name=basename(attachment))
            part['Content-Disposition'] = (
                'attachment; filename="%s"' % basename(attachment))
            msg.attach(part)

        self.smtp_server.sendmail(frm, rcpts, msg.as_string())

    def send_welcome_email(self, to, firstname, lastname, password):
        to_list = [to]
        cc_list = [
            "changeme@tedxdresden.com",
            "changeme@tedxdresden.com",
            "changeme@tedxdresden.com",
            "changeme@tedxdresden.com"
        ]
        subject = "Your account details and a walk-through TEDxDresden :)"
        attachments = [
            "2017-11-03_IT_Introduction_Excerpt.pdf",
            "2018-02-01_Organigramm.pdf"
         ]

        with open('welcome_email_template', 'r') as welcome_email_template:
            body = welcome_email_template.read()

            body = body.format(
                firstname=firstname, lastname=lastname, password=password)

            self.send_email(
                to_list, cc_list, subject, body, attachments=attachments)

            print("Sent welcome email to...{}".format(to_list))


class Trello:
    def __init__(self):
        self.token = MY_TRELLO_TOKEN
        self.key = MY_TRELLO_KEY
        self.base_url = 'https://api.trello.com/1/organizations/tedxdresden'

    def create_user(self, firstname, lastname, email):
        creation_url = "{}/members".format(self.base_url)

        payload = {
            'key': self.key,
            'token': self.token,
            'email': email,
            'fullName': '{0}.{1}'.format(firstname, lastname)
        }

        result = requests.request('PUT', creation_url, params=payload)
        print("Trello user creation...")
        print(result.json())


class Slack:
    def __init__(self):
        self.organization = 'tedxdresden'
        self.token = MY_SLACK_TOKEN
        self.base_url = 'https://{}.slack.com/api'.format(self.organization)
        self.client = SlackClient(self.token)

    def list_channels(self):
        return self.client.api_call(
            "channels.list", exclude_archived=1)["channels"]

    def invite_member(self, email, channel_names):
        channels_list = self.list_channels()
        channel_ids = []

        for channel in channels_list:
            if channel["name_normalized"] in channel_names:
                channel_ids.append(channel["id"])

        timestamp = int(datetime.now().timestamp())
        admin_invite_url = '{}/users.admin.invite?t={}'.format(
            self.base_url, timestamp)

        payload = {
            'email': email,
            'token': self.token,
            'channels': ",".join(channel_ids),
            'set_active': True
        }

        headers = {
            'cache-control': "no-cache"
        }

        res = requests.request(
            'POST', admin_invite_url, headers=headers, params=payload)

        # See what gets sent back
        print("Slack member invitation...")
        print('Got: {}'.format(res.status_code))
        print(res.text)


class GSuite:
    def __init__(self):
        self.credentials = self.get_credentials()
        self.service = self.get_service()
        self.users = self.service.users()
        self.groups = self.service.groups()
        self.members = self.service.members()

    def get_service(self):
        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('admin', 'directory_v1', http=http)
        return service

    def get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(
            credential_dir, 'admin-directory_v1-python-quickstart.json')

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else:   # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials

    def add_user_to_group(self, user_email, group_email):
        self.members.insert(
            groupKey=group_email,
            body={
                "email": user_email
            }
        ).execute()

    def create_user(self, user_dict):
        firstname = user_dict["firstname"]
        lastname = user_dict["lastname"]
        groups = user_dict["groups"]
        personal_email = user_dict["personal_email"]
        mobile_num = user_dict["mobile_num"]
        user_email = "{0}.{1}@tedxdresden.com".format(firstname, lastname)
        random_password = simple_pass_gen()
        created_user = self.users.insert(
            body={
                "isAdmin": False,
                "primaryEmail": user_email,
                "name": {
                    "givenName": firstname,
                    "familyName": lastname
                },
                "password": random_password,
                "changePasswordAtNextLogin": True,
                "orgUnitPath": "/Regular People",
                "emails": [
                 {
                  "address": personal_email,
                  "type": "home",
                  "customType": "",
                  "primary": False
                 }
                ],
                "phones": [
                 {
                  "value": mobile_num,
                  "type": "home"
                 }
                ],
            }
        ).execute()

        self.add_user_to_group(
            user_email, "changeme@tedxdresden.com")

        for group in groups:
            self.add_user_to_group(user_email, group)

        created_user["random_password"] = random_password
        created_user["user_email"] = user_email
        print("GSuite account creation....")
        print(created_user)
        return created_user

    def delete_user(self, userKey):
        return self.users.delete(userKey=userKey).execute()


def main():

    gsuite = GSuite()
    email_wrapper = EmailWrapper()
    slack = Slack()
    trello = Trello()

    new_users = [
        {
            "firstname": "Wallas",
            "lastname": "Testing",
            "personal_email": "0x999@maildu.de",
            "mobile_num": "+4912345678",
            "groups": [

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",

                "changeme@tedxdresden.com",
            ]
        }
    ]

    for new_user in new_users:
        firstname = new_user["firstname"]
        lastname = new_user["lastname"]
        personal_email = new_user["personal_email"]

        # Create GSuite account
        new_user = gsuite.create_user(new_user)
        tedx_email = new_user["user_email"]
        # Wait 10 secs
        time.sleep(10)
        # Invite GSuite account to slack
        slack.invite_member(tedx_email, ["1_general"])
        # Invite GSuite account to trello
        trello.create_user(firstname, lastname, tedx_email)
        new_user_password = new_user["random_password"]
        # Send welcome email
        email_wrapper.send_welcome_email(
            personal_email, firstname, lastname, new_user_password)


if __name__ == '__main__':
    main()
