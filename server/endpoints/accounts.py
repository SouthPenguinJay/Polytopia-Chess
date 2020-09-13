"""Respond to API calls.

This module does not handle encryption.
"""
import datetime
import hashlib
import typing

import peewee

import requests

import config
import emails
import models

from .helpers import RequestError, paginate


def _validate_username(username: str):
    """Validate a username.

    This does not enforce uniqueness.
    """
    if not username:
        raise RequestError(1112)
    elif len(username) > 32:
        raise RequestError(1111)


def _validate_password(password: str):
    """Validate that a password meets security requirements.

    Also checks against the haveibeenpwned.com database.
    """
    if len(password) < 10:
        raise RequestError(1121)
    if len(password) > 32:
        raise RequestError(1122)
    if len(set(password)) < 6:
        raise RequestError(1123)
    sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    hash_range = sha1_hash[:5]
    resp = requests.get(
        'https://api.pwnedpasswords.com/range/' + hash_range,
        headers={'Add-Padding': 'true'}
    )
    for line in resp.text.split('\n'):
        if line:
            hash_suffix, count = line.split(':')
            if int(count) and hash_range + hash_suffix == sha1_hash:
                raise RequestError(1124)


def _validate_email(email: str):
    """Validate that an email is of a valid format.

    Does not validate that the address actualy exists/is in use.
    Doesn't actually come close to validating that the email address, that is
    not very necessary though.
    """
    if len(email) > 255:
        raise RequestError(1130)
    parts = email.split('@')
    if len(parts) < 2:
        raise RequestError(1131)
    if len(parts) > 2:
        if not (parts[0].startswith('"') and parts[-2].endswith('"')):
            raise RequestError(1131)


def create_account(username: str, password: str, email: str):
    """Create a new user account."""
    _validate_username(username)
    _validate_password(password)
    _validate_email(email)
    try:
        user = models.User.create(
            username=username, password=password, email=email
        )
    except peewee.IntegrityError:
        raise RequestError(1113)
    send_verification_email(user)


def send_verification_email(user: models.User):
    """Send a verification email to a user."""
    if user.email_verified:
        raise RequestError(1201)
    url = (
        f'https://{config.HOST_URL}/accounts/verify_email/'
        f'{user.username}/{user.email_verify_token}'
    )
    message = f'Please click here to verify your email address: {url}'
    emails.send_email(user.email, message)


def verify_email(username: str, token: str):
    """Verify an email address."""
    try:
        user = models.User.get(
            models.User.username == username,
            models.User.email_verify_token == token
        )
    except peewee.DoesNotExist:
        raise RequestError(1202)
    user.email_verified = True
    user.save()


def update_account(
        user: models.User,
        password: typing.Optional[str] = None,
        avatar: typing.Optional[bytes] = None,
        email: typing.Optional[str] = None):
    """Update a user's account."""
    if password:
        _validate_password(password)
        user.password = password
    if email:
        _validate_email(email)
        user.email = email
        send_verification_email(user)
    if avatar:
        # FIXME: Some validation that the avatar is actually an image?
        #        Maybe a maximum size, too? Should media really be stored in
        #        the database? Is there a better way?
        user.avatar = avatar
    user.save()


def get_account(username: str) -> typing.Dict[str, typing.Any]:
    """Get a user account."""
    try:
        user = models.User.get(
            models.User.username == username
        )
    except peewee.DoesNotExist:
        raise RequestError(1003)
    return {
        'id': user.id,
        'username': username,
        'elo': user.elo,
        'avatar': None    # FIXME: Should be a url, how are we gonna do media?
    }


def get_accounts(page: int) -> typing.Dict[str, typing.Any]:
    """Get a paginated list of accounts."""
    users, pages = paginate(models.User.select(), page)
    users = [
        {
            'id': user.id,
            'username': user.username,
            'elo': user.elo,
            'avatar': None    # FIXME: Should be a url, see above
        } for user in users
    ]
    return {
        'users': users,
        'pages': pages
    }


def delete_account(user: models.User):
    """Delete a user's account."""
    for game in user.games:
        if game.host == user:
            if game.away:
                game.winner = models.Winner.AWAY
                game.conclusion_type = models.Conclusion.RESIGN
                game.ended_at = datetime.datetime.now()
                game.save()
            else:
                game.delete_instance(recursive=True)
        else:
            game.winner = models.Winner.HOME
            game.conclusion_type = models.Conclusion.RESIGN
            game.ended_at = datetime.datetime.now()
            game.save()
    user.delete_instance()
