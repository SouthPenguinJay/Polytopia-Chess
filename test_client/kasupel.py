"""A Python wrapper for the API."""
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

import socketio


Json = typing.Dict[str, typing.Any]


def load_timestamp(seconds: int) -> datetime.datetime:
    """Load a datetime from an int."""
    if seconds is None:
        return None
    return datetime.datetime.fromtimestamp(seconds)


def dump_timestamp(x: datetime.datetime) -> int:
    """Convert a datetime to an int."""
    return int(x.timestamp())


def load_timedelta(seconds: int) -> datetime.timedelta:
    """Load a timedelta from an int."""
    if seconds is None:
        return None
    return datetime.timedelta(seconds=seconds)


def dump_timedelta(x: datetime.timedelta) -> int:
    """Convert a timedelta to an int."""
    return int(x.total_seconds())


class RequestError(Exception):
    """A class for errors caused by a bad request."""

    def __init__(self, error: Json):
        """Store the code and message to be handled."""
        self.code = error['error']
        self.message = error['message']
        super().__init__(f'ERR{self.code}: {self.message}.')


class Gamemode(enum.Enum):
    """An enum for the mode of a game."""

    CHESS = enum.auto()


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


class PieceType(enum.Enum):
    """An enum for a chess piece type."""

    PAWN = enum.auto()
    ROOK = enum.auto()
    KNIGHT = enum.auto()
    BISHOP = enum.auto()
    QUEEN = enum.auto()
    KING = enum.auto()


class Client:
    """A client connected to the server."""

    def __init__(self, url: str):
        """Initialise the client with the URL of the server."""
        self.url = url

    def _post_payload(
            self, endpoint: str, payload: Json, method: str = 'POST',
            encrypted: bool = False) -> Json:
        """Encrypt a payload and send it to the server."""
        data = json.dumps(payload, separators=(',', ':')).encode()
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
        response = method(self.url + endpoint, data=data)
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Json:
        """Handle a response from the server."""
        if response.ok:
            if response.status_code == 204:
                return {}
            else:
                return response.json()
        raise RequestError(response.json())

    @functools.cached_property
    def _public_key(self) -> rsa.RSAPublicKey:
        """Get the server's public key."""
        raw = requests.get(self.url + '/rsa_key').content
        return serialization.load_pem_public_key(raw)

    def login(self, username: str, password: str) -> Session:
        """Log in to an account."""
        token = base64.b64encode(os.urandom(32)).decode()
        resp = self._post_payload('/accounts/login', {
            'username': username,
            'password': password,
            'token': token
        }, encrypted=True)
        session_id = resp['session_id']
        return Session(self, token, session_id)

    def get_user(self, username: str = None, user_id: int = None) -> User:
        """Get a user's account."""
        if not bool(username) ^ bool(id):
            raise TypeError('Exactly one of username or id should be passed.')
        if username:
            resp = requests.get(self.url + '/user/' + username)
        else:
            resp = requests.get(
                self.url + '/accounts/account', params={'id': user_id}
            )
        return User(self, self._handle_response(resp))

    def get_game(self, game_id: int) -> Game:
        """Get a game by ID."""
        resp = requests.get(self.url + '/games/' + str(game_id))
        return Game(self, self._handle_response(resp))

    def get_users(self, start_page: int = 0) -> Paginator:
        """Get a list of all users."""
        return Paginator(self, '/accounts/all', 'users', User, start_page)

    def create_account(self, username: str, password: str, email: str):
        """Create a new user account."""
        self._post_payload('/accounts/create', {
            'username': username,
            'password': password,
            'email': email
        }, encrypted=True)

    def verify_email(self, username: str, token: str):
        """Verify an email address."""
        resp = requests.get(self.url + '/accounts/verify_email', params={
            'username': username, 'token': token
        })
        self._handle_response(resp)


class Session:
    """An authenticated session."""

    def __init__(self, client: Client, token: str, session_id: str):
        """Start the session."""
        self.token = token
        self.id = session_id
        self.client = client

    def _get_authenticated(
            self, endpoint: str, payload: Json = None,
            method: str = 'GET') -> Json:
        """Get an endpoint that requires authentication."""
        payload = payload or {}    # Avoid mutable parameter default.
        payload['session_id'] = self.id
        payload['session_token'] = self.token
        method = {
            'GET': requests.get,
            'DELETE': requests.delete
        }[method]
        response = method(self.client.url + endpoint, params=payload)
        return self.client._handle_response(response)

    def _post_authenticated(
            self, endpoint: str, payload: Json,
            method: str = 'POST', encrypted: bool = False) -> Json:
        """Post to an endpoint that requires authentication."""
        payload['session_id'] = self.id
        payload['session_token'] = self.token
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
            self, endpoint: str, start_page: int,
            **params: Json) -> Paginator:
        """Get a paginated list of games."""
        params['session_id'] = self.id
        params['session_token'] = self.token
        return Paginator(
            client=self.client,
            endpoint='/games/' + endpoint,
            main_field='games',
            model=Game,
            start_page=start_page,
            params=params,
            reference_fields={
                'host': 'users', 'away': 'users', 'invited': 'users'
            }
        )

    def get_common_completed_games(
            self, other: User, start_page: int = 0) -> Paginator:
        """Get a list of games this user has in common with someone else."""
        return self._get_games_paginator(
            'common_completed', start_page, account=other.username
        )

    def get_invites(self, start_page: int = 0) -> Paginator:
        """Get a list of games this user has been invited to."""
        return self._get_games_paginator('invites', start_page)

    def get_searches(self, start_page: int = 0) -> Paginator:
        """Get a list of outgoing game searches this user has."""
        return self._get_games_paginator('searches', start_page)

    def get_ongoing(self, start_page: int = 0) -> Paginator:
        """Get a list of ongoing games this user is in."""
        return self._get_games_paginator('ongoing', start_page)

    def find_game(
            self,
            main_thinking_time: datetime.timedelta,
            fixed_extra_time: datetime.timedelta,
            time_increment_per_turn: datetime.timedelta,
            mode: Gamemode) -> Game:
        """Look for or create a game."""
        response = self._post_authenticated(
            '/games/find', {
                'main_thinking_time': dump_timedelta(main_thinking_time),
                'fixed_extra_time': dump_timedelta(fixed_extra_time),
                'time_increment_per_turn': dump_timedelta(
                    time_increment_per_turn
                ),
                'mode': mode.value
            }
        )
        return self.client.get_game(response['game_id'])

    def send_invitation(
            self, other: User,
            main_thinking_time: datetime.timedelta,
            fixed_extra_time: datetime.timedelta,
            time_increment_per_turn: datetime.timedelta,
            mode: Gamemode) -> Game:
        """Send an invitation to another user."""
        response = self._post_authenticated(
            '/games/send_invitation', {
                'invitee': other.username,
                'main_thinking_time': dump_timedelta(main_thinking_time),
                'fixed_extra_time': dump_timedelta(fixed_extra_time),
                'time_increment_per_turn': dump_timedelta(
                    time_increment_per_turn
                ),
                'mode': mode.value
            }
        )
        return self.client.get_game(response['game_id'])

    def accept_inivitation(self, invitation: Game):
        """Accept a game you have been invited to."""
        self._post_authenticated('/games/invites/' + str(invitation.id), {})

    def decline_invitation(self, invitation: Game):
        """Decline a game you have been invited to."""
        self._get_authenticated(
            '/games/invites/' + str(invitation.id), method='DELETE'
        )

    def connect_to_game(self, game: Game) -> GameConnection:
        """Connect to a websocket for a game."""
        return GameConnection(self, game)


class GameConnection(socketio.Client):
    """A websocket connection for a game."""

    def __init__(self, session: Session, game: Game):
        """Connect to the game."""
        super().__init__()
        self.session = session
        self.client = session.client
        self.game = game
        session_token = base64.b64encode(self.session.token)
        headers = {
            'Game-ID': game.id,
            'Authorization': f'SessionKey {self.session.id}|{session_token}'
        }
        self.connect(self.client.url, headers=headers)

    def request_game_state(self):
        """Request the current state of the game."""
        self.emit('game_state')

    def request_allowed_moves(self):
        """Request the moves we are allowed to make."""
        self.emit('allowed_moves')

    def make_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int, promotion: typing.Optional[PieceType] = None):
        """Make a move."""
        self.emit('move', {
            'start_rank': start_rank,
            'start_file': start_file,
            'end_rank': end_rank,
            'end_file': end_file,
            'promotion': (promotion.value if promotion else None)
        })

    def offer_draw(self):
        """Offer our opponent a draw."""
        self.emit('offer_draw')

    def claim_draw(self, reason: Conclusion):
        """Claim a draw."""
        self.emit('claim_draw', reason.value)

    def resign(self):
        """Resign from the game."""
        self.emit('resign')

    # TODO: Accept incoming events.


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
        self.mode = Gamemode(data['mode'])
        self.host = User(client, data['host']) if data['host'] else None
        self.away = User(client, data['away']) if data['away'] else None
        self.invited = (
            User(client, data['invited']) if data['invited'] else None
        )
        self.current_turn = Side(data['current_turn'])
        self.turn_number = data['turn_number']
        self.main_thinking_time = load_timedelta(data['main_thinking_time'])
        self.fixed_extra_time = load_timedelta(data['fixed_extra_time'])
        self.time_increment_per_turn = load_timedelta(
            data['time_increment_per_turn']
        )
        self.home_time = load_timedelta(data['home_time'])
        self.away_time = load_timedelta(data['away_time'])
        self.home_offering_draw = data['home_offering_draw']
        self.away_offering_draw = data['away_offering_draw']
        self.winner = Winner(data['winner'])
        self.conclusion_type = Conclusion(data['conclusion_type'])
        self.opened_at = load_timestamp(data['opened_at'])
        self.started_at = load_timestamp(data['started_at'])
        self.last_turn = load_timestamp(data['last_turn'])
        self.ended_at = load_timestamp(data['ended_at'])

    def __eq__(self, other: Game) -> bool:
        """Check if another instance refers to the same game."""
        return isinstance(other, Game) and other.id == self.id


class Paginator:
    """A paginated list of entities from the API."""

    def __init__(
            self, client: Client, endpoint: str, main_field: str,
            model: typing.Any, start_page: int = 0, params: Json = None,
            reference_fields: typing.Dict[str, str] = None):
        """Initialise the paginator."""
        self.client = client
        self._page = None
        self.page_number = start_page
        self.pages = None
        self._index = 0
        self.per_page = 100
        self._endpoint = endpoint
        self._params = params or {}
        self._main_field = main_field
        self._reference_fields = reference_fields or {}
        self._model = model

    def _get_page(self):
        """Fetch the current page."""
        self._params['page'] = self.page_number
        response = requests.get(
            self.client.url + self._endpoint, params=self._params
        )
        raw = self.client._handle_response(response)
        self.pages = raw['pages']
        self._page = []
        for data in raw[self._main_field]:
            for field in data:
                if field in self._reference_fields:
                    if data[field]:
                        data[field] = raw[
                            self._reference_fields[field]
                        ][str(data[field])]
            self._page.append(self._model(self.client, data))

    def __iter__(self) -> Paginator:
        """Initialise this as an iterable."""
        self._index = 0
        self._get_page()
        self.per_page = len(self._page)
        return self

    def __next__(self) -> User:
        """Get the next item."""
        if self._index < len(self._page):
            value = self._page[self._index]
            self._index += 1
            return value
        elif self.page_number + 1 < self.pages:
            self.page_number += 1
            self._get_page()
            self._index = 1
            return self._page[0]
        else:
            raise StopIteration

    def __len__(self) -> int:
        """Calculate an aproximate for the number of items."""
        return self.pages * self.per_page
