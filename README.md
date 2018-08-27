## TEDxDD cockpit
This repository serves as an admin cockpit to manage accounts, groups, channels, boards, ...etc) across all web services used by TEDxDD. At the moment, we focus on Trello, Slack, and G-Suite.

### How to use
1. Provide the necessary files: `2017-11-03_IT_Introduction_Excerpt.pdf`, `2018-02-01_Organigramm.pdf`.
2. Provide the necessary secret files: `client_secret.json`, `my_slack_token`, `my_tedxdd_email_passwd`, `my_trello_key`, `my_trello_token`.
3. Provide the necessary welcome email template file: `welcome_email_template`.
4. Modify the email addresses `changeme@tedxdresden.com` in `quickstart.py` accordingly.
5. Look at the `new_users` variable in `quickstart.py` and adjust accordingly to add/remove users.
6. Run `python3 quickstart.py`.
