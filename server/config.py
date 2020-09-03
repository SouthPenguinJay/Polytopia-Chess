"""Load the config settings."""
import json


with open('config.json') as f:
    config = json.load(f)


DB_NAME = config['db_name']
DB_USER = config.get('db_user', DB_NAME)
DB_PASSWORD = config.get('db_password', '')
