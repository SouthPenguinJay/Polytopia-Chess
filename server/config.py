"""Load the config settings."""
import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


with open('config.json') as f:
    config = json.load(f)


DB_NAME = config['db_name']
DB_USER = config.get('db_user', DB_NAME)
DB_PASSWORD = config.get('db_password', '')


SMTP_SERVER = config['smtp_server']
SMTP_PORT = config.get('smtp_port', 465)
SMTP_USERNAME = config.get('smtp_username', 'apikey')
SMTP_PASSWORD = config['smtp_password']
EMAIL_ADDRESS = config['email_address']

HOST_URL = config['host_url']

# Get the public/private key pair or generate if not found.
_raw_key = config.get('private_key')

if _raw_key:
    PRIVATE_KEY = serialization.load_pem_private_key(
        base64.b64decode(_raw_key), password=None
    )
else:
    # FIXME: Vulnerable to MITM attack - we need a certificate.
    PRIVATE_KEY = rsa.generate_private_key(
        public_exponent=65537, key_size=4096
    )
    _raw_key = PRIVATE_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    config['private_key'] = base64.b64encode(_raw_key).decode()
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

PUBLIC_KEY = PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode()
