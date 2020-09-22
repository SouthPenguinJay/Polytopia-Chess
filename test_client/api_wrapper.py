"""Test the server with a terminal client."""
from __future__ import annotations

import base64
import datetime
import enum
import functools
import json
import os
import typing

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

import requests


URL = 'https://127.0.0.1:5000'

Json = typing.Dict[str, typing.Any]


def load_timedelta(seconds: int) -> datetime.timedelta:
    """Load a timedelta from an int."""
    return datetime.timedelta(seconds=seconds)


load_timestamp = datetime.datetime.fromtimestamp


class RequestError(Exception):
    """A class for errors caused by a bad request."""

    def __init__(self, error: Json):
        """Store the code and message to be handled."""
        self.code = error['error']
        self.message = error['message']
        super().__init__(f'ERR{self.code}: {self.message}.')


class Winner(enum.Enum):
    """An enum for the winner of a game."""

    GAME_NOT_COMPLETE = enum.auto()
    HOME = enum.auto()
    AWAY = enum.auto()
    DRAW = enum.auto()


class Conclusion(enum.Enum):
    """An enum for the way a game finished."""

    GAME_NOT_COMPLETE = enum.auto()
    CHECKMATE = enum.auto()
    RESIGN = enum.auto()
    TIME = enum.auto()
    STALEMATE = enum.auto()
    THREEFOLD_REPETITION = enum.auto()
    FIFTY_MOVE_RULE = enum.auto()
    AGREED_DRAW = enum.auto()


class Side(enum.Enum):
    """An enum for home/away."""

    HOME = enum.auto()
    AWAY = enum.auto()


class Client:
    """A client connected to the server."""

    def _post_payload(
            self, endpoint: str, payload: Json, method: str = 'POST',
            encrypted: bool = False) -> Json:
        """Encrypt a payload and send it to the server."""
        data = json.dumps(payload, separators=(',', ':'))
        if encrypted:
            data = self._public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        method = {
            'POST': requests.post,
            'PATCH': requests.patch
        }[method]
        response = method(URL + endpoint, data=data)
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Json:
        """Handle a response from the server."""
        if response.ok:
            return response.json()
        raise RequestError(response.json())

    @functools.cached_property
    def _public_key(self) -> rsa.RSAPublicKey:
        """Get the server's public key."""
        raw = requests.get(URL + '/rsa_key').content
        return serialization.load_pem_public_key(raw)

    def login(self, username: str, password: str) -> Session:
        """Log in to an account."""
        return Session(self, username, password)

    def get_user(self, username: str = None, id: int = None) -> User:
        """Get a user's account."""
        if not bool(username) ^ bool(id):
            raise TypeError('Exactly one of username or id should be passed.')
        if username:
            resp = requests.get(URL + '/user/' + username)
        else:
            resp = requests.get(URL + '/accounts/account', params={'id': id})
        return User(self, self._handle_response(resp))

    def get_users(self) -> Paginator:
        """Get a list of all users."""
        return Paginator(self, '/accounts/all', 'users', User)

    def create_account(self, username: str, password: str, email: str):
        """Create a new user account."""
        self._post_payload('/accounts/create', {
            'username': username,
            'password': password,
            'email': email
        }, encrypted=True)


class Session:
    """An authenticated session."""

    def __init__(self, client: Client, username: str, password: str):
        """Start the session."""
        self._token = base64.b64encode(os.urandom(32)).decode()
        resp = client._post_encrypted_payload('/accounts/login', {
            'username': username,
            'password': password,
            'token': self._token
        })
        self._session_id = resp['session_id']
        self.client = client

    def _get_authenticated(
            self, endpoint: str, payload: Json = None,
            method: str = 'GET') -> Json:
        """Get an endpoint that requires authentication."""
        payload = payload or {}    # Avoid mutable parameter default.
        payload['session_id'] = self._session_id
        payload['session_token'] = self._token
        method = {
            'GET': requests.get,
            'DELETE': requests.delete
        }[method]
        response = method(URL + endpoint, params=payload)
        return self.client._handle_response(response)

    def _post_authenticated(
            self, endpoint: str, payload: Json,
            method: str = 'POST', encrypted: bool = False) -> Json:
        """Post to an endpoint that requires authentication."""
        payload['session_id'] = self._session_id
        payload['session_token'] = self._token
        return self.client._post_payload(endpoint, payload, method, encrypted)

    def _invalidate_user_cache(self):
        """Invalidate the cached associated user."""
        try:
            del self.user    # Invalidate cache
        except AttributeError:
            pass             # Was not cached anway

    def logout(self):
        """End the session."""
        self._get_authenticated('/accounts/logout')

    def resend_verification_email(self):
        """Resend the verification email for an account."""
        self._get_authenticated('/accounts/resend_verification_email')

    def update(self, password: str = None, email: str = None):
        """Update the user's account."""
        payload = {}
        if password:
            payload['password'] = password
        if email:
            payload['email'] = email
        self._invalidate_user_cache()
        self._post_authenticated('/accounts/me', payload, 'PATCH', True)

    @functools.cached_property
    def user(self) -> User:
        """Get the user's account details."""
        details = self._get_authenticated('/accounts/me')
        return User(self.client, details)

    def fetch_user(self) -> User:
        """Get the user's account details (without caching)."""
        self._invalidate_user_cache()
        return self.user

    def delete(self):
        """Delete the user's account."""
        self._get_authenticated('/accounts/me', method='DELETE')

    def _get_games_paginator(
            self, endpoint: str, **params: Json) -> Paginator:
        """Get a paginated list of games."""
        params['session_id'] = self._session_id
        params['session_token'] = self._token
        return Paginator(
            client=self.client,
            endpoint='/games/' + endpoint,
            main_field='games',
            model=Game,
            params=params,
            reference_fields={
                'host': 'users', 'away': 'users', 'invited': 'users'
            }
        )

    def get_common_completed_games(self, other: User) -> Paginator:
        """Get a list of games this user has in common with someone else."""
        return self._get_games_paginator(
            'common_completed', account=other.username
        )

    def get_invites(self) -> Paginator:
        """Get a list of games this user has been invited to."""
        return self._get_games_paginator('invites')

    def get_searches(self) -> Paginator:
        """Get a list of outgoing game searches this user has."""
        return self._get_games_paginator('searches')

    def get_ongoing(self) -> Paginator:
        """Get a list of ongoing games this user is in."""
        return self._get_games_paginator('ongoing')

    def decline_invitation(self, invitation: Game):
        """Decline a game you have been invited to."""
        self._get_authenticated(
            '/games/invites/' + str(invitation.id), method='DELETE'
        )

    # TODO: Implement sockets


class User:
    """A user from the API."""

    def __init__(self, client: Client, data: Json):
        """Load the user attributes."""
        self.client = client
        self.id = data['id']
        self.username = data['username']
        self.elo = data['elo']
        self.created_at = load_timestamp(data['created_at'])
        if 'email' in data:
            # If this is was fetched as the currently authenticated user.
            self.email = data['email']
            self.authenticated = True
        else:
            self.authenticated = False

    def get_completed_games(self) -> Paginator:
        """Get a paginated list of games this user has completed."""
        return Paginator(
            client=self.client,
            endpoint='/games/completed',
            main_field='games',
            model=Game,
            params={'account': self.username},
            reference_fields={
                'host': 'users', 'away': 'users', 'invited': 'users'
            }
        )

    def __eq__(self, other: User) -> bool:
        """Check if another instance refers to the same user."""
        return isinstance(other, User) and other.id == self.id


class Game:
    """A game from the API."""

    def __init__(self, client: Client, data: Json):
        """Load the game attributes."""
        self.client = client
        self.id = data['id']
        self.mode = data['mode']
        self.main_thinking_time = load_timedelta(data['main_thinking_time'])
        self.fixed_extra_time = load_timedelta(data['fixed_extra_time'])
        self.time_increment_per_turn = load_timedelta(
            data['time_increment_per_turn']
        )
        self.host = data.get('host')
        self.started = 'started_at' in data
        self.ongoing = 'last_turn' in data
        self.ended = 'ended_at' in data
        self.is_invitation = 'invited' in data
        if self.started:
            self.started_at = load_timestamp(data['started_at'])
            self.away = data.get('away')
        else:
            self.opened_at = load_timestamp(data['opened_at'])
        if self.is_invitation:
            self.invited = data['invited']
        if self.ended:
            self.ended_at = load_timestamp(data['ended_at'])
            self.conclusion_type = Conclusion(data['conclusion_type'])
            self.winner = Side(data['winner'])
        if self.ongoing:
            self.last_turn = load_timestamp(data['last_turn'])
            self.turn_number = data['turn_number']
            self.current_turn = Side(data['current_turn'])

    def __eq__(self, other: Game) -> bool:
        """Check if another instance refers to the same game."""
        return isinstance(other, Game) and other.id == self.id


class Paginator:
    """A paginated list of entities from the API."""

    def __init__(
            self, client: Client, endpoint: str, main_field: str,
            model: typing.Any, params: Json = None,
            reference_fields: typing.Dict[str, str] = None):
        """Initialise the paginator."""
        self.client = client
        self._page = None
        self._page_number = 0
        self._pages = None
        self._index = 0
        self._per_page = 100
        self._endpoint = endpoint
        self._params = params or {}
        self._main_field = main_field
        self._reference_fields = reference_fields or {}
        self._model = model

    def _get_page(self):
        """Fetch the current page."""
        self._params['page'] = self._page_number
        response = requests.get(URL + self._endpoint, params=self._params)
        raw = self.client._handle_response(response)
        self._pages = raw['pages']
        self._page = []
        for data in raw[self._main_field]:
            for field in data:
                if field in self._reference_fields:
                    data[field] = raw[
                        self._reference_fields[field]
                    ][data[field]]
            self._page.append(self._model(self.client, data))

    def __iter__(self) -> Paginator:
        """Initialise this as an iterable."""
        self._index = 0
        self._page_number = 0
        self._get_page()
        self._per_page = len(self._page)
        return self

    def __next__(self) -> User:
        """Get the next user."""
        if self._index + 1 < len(self._page):
            value = self._page[self._index]
            self._index += 1
            return value
        elif self._page_number + 1 < self._pages:
            self._page_number += 1
            self._get_page()
            self._index = 1
            return self._page[0]
        else:
            raise StopIteration

    def __len__(self) -> int:
        """Calculate an aproximate for the number of users."""
        return self._pages * self._per_page
