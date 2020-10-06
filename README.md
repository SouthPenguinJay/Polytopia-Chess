# Kasupel

A chess game with custom pieces and boards. Join the discord https://discord.gg/55NwUbD.

## Setting up the server

### 1: Install Python

The Python version must be of the form 3.x, where x >= 8 (no Python 2.x, Python 3.6 or Python 4, for example).

Python can be installed from the [official website](https://www.python.org/downloads/), or on Debain, with `sudo apt install python3.8 python3.8-dev`. Python may already be installed on some systems, but make sure the version is up to date.

### 2: Install dependencies from PyPI

This may be as simple as `pip install -r server/requirements.txt -U`, but depending on your setup you may need to replace `pip` with `pip3`, `py -m pip`, `py3 -m pip`, `python3 -m pip`, `python3.8 -m pip`...

### 3: Create a config file

This should be in `server/config.json`. To start with, it should simply contain:
```
{
}
```
We will add more content to it as we set up.

### 4: Set up Postgres

  1. Install Postgres, if you haven't already
  2. Create a new Postgres role, eg. `kasupel`.
  3. Create a database for the role, eg. `kasupel`.
  4. Add to following lines to the config file (between the `{` and `}`):
     ```
         "db_name": "kasupel",
         "db_user": "kasupel",
         "db_password": "******",
     ```
     Of course, replace the values with those chosen in the above steps.

### 5: Set up SMTP

  1. Decide on a SMTP server to use. Your ISP may provide one, or you can use [Sendgrid](https://sendgrid.com/) free for 100 emails per day.
  2. Find out the server URL, port (for SSL), username and password you will need to use for your chosen SMTP server. Also find out the email address you will be given.
  3. Add these to the config file, as follows:
     ```
        "smtp_server": "<server URL>",
        "smtp_port": <port number>,
        "smtp_username": "username-goes-here",
        "smtp_password": "***********",
        "email_address": "Display Name <address@domain.tld>"
     ```

### 6: Run the server

Run `server/` as a Python module, eg. `python3 -m server`.

TODO: Add instructions for running in production, maybe.
