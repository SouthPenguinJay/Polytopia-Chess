"""Various Peewee models."""
import config

import peewee as pw

import datetime
import hashlib


HASHING_ALGORITHM = hashlib.sha3_512

db = pw.PostgresqlDatabase(
    config.DB_NAME, user=config.DB_USER, password=config.DB_PASSWORD
)


class HashedPassword:
    """A class to check for equality against hashed passwords."""

    def __init__(self, hashed_password: str):
        """Store the hashed password."""
        self.hashed_password = hashed_password

    def __eq__(self, password: str):
        """Check for equality against an unhashed password."""
        hashed_attempt = HASHING_ALGORITHM(password.encode()).hexdigest()
        return hashed_attempt == self.hashed_password


class BaseModel(pw.Model):
    """A base model, that sets the DB."""

    class Meta:
        """Set the DB and use new table names."""

        database = db
        use_legacy_table_names = False


class User(BaseModel):
    """A model to represent a user."""

    username = pw.CharField(max_length=32, unique=True)
    password_hash = pw.FixedCharField(max_length=128)
    email = pw.CharField(max_length=255, unique=True)
    email_verified = pw.BooleanField(default=False)
    elo = pw.SmallIntegerField(default=1000)
    avatar = pw.BlobField(null=True)
    created_at = pw.DateTimeField(default=datetime.datetime.now)

    @property
    def password(self) -> HashedPassword:
        """Return an object that will use hashing in it's equality check."""
        return HashedPassword(self, password_hash)

    @password.setter
    def password(self, password: str):
        """Set the password to a hash of the provided password."""
        self.password_hash = HASHING_ALGORITHM(password.encode()).hexdigest()


class Game(BaseModel):
    """A model to represent a game.
    
    The game may be in any of the following states:
      1. Open
          A player is looking for a game matching these specs, but a second
          player has yet to be found.
      2. In progress
          There are two players in this game, who are currently playing.
      3. Completed
          This game has ended - either there is a winner, or it was a draw.
    """

    host = pw.ForeignKeyField(model=User, backref='games')
    away = pw.ForeignKeyField(model=User, backref='games', null=True)
    mode = pw.SmallIntegerField(default=1)    # only valid value for now
    seconds_per_game = pw.IntegerField()      # timer at the start of the game
    seconds_per_turn = pw.IntegerField()      # timer incremement per turn
    home_time = pw.IntegerField()             # timer for home
    away_time = pw.IntegerField()             # timer for away
    home_offering_draw = pw.BooleanField(default=False)
    away_offering_draw = pw.BooleanField(default=False)
    # TODO: Represent the board somehow.

    # 0=not finished, 1=home, 2=away, 3=draw
    winner = pw.SmallIntegerField(default=0)

    # 0=not finished, 1=checkmate, 2=resign, 3=agreed draw, 4=stalemate
    # 5=threefold repetition, 6=50 move rule, 7=time
    # TODO: Are there more possible conclusions?
    conclusion_type = pw.SmallIntegerField(default=0)

    opened_at = pw.DateTimeField(default=datetime.datetime.now)
    started_at = pw.DateTimeField(null=True)
    ended_at = pw.DateTimeField(null=True)


db.create_tables([User, Game])
