"""Socket event handlers and emitters."""
import datetime
import typing

import flask

from . import connections, helpers
from .. import models, ratings


def has_started(game: models.Game):
    """Inform all connected users that a game has started."""
    helpers.send_room('game_start', {}, str(game.id))


def get_game_state(game: models.Game) -> typing.Dict[str, typing.Any]:
    """Send the game state for an ongoing game."""
    pieces = models.Piece.select().where(models.Piece.game == game)
    board = {}
    for piece in pieces:
        board[f'{piece.rank},{piece.file}'] = (
            piece.piece_type.value, piece.side.value
        )
    last_turn = game.last_turn or game.started_at
    return {
        'board': board,
        'home_time': game.home_time.total_seconds(),
        'away_time': game.away_time.total_seconds(),
        'last_turn': last_turn.timestamp(),
        'current_turn': game.current_turn.value,
        'turn_number': int(game.turn_number)
    }


def get_allowed_moves(game: models.Game) -> typing.Dict[str, typing.Any]:
    """Get allowed moves for the user whos turn it is."""
    moves = list(game.game_mode.possible_moves(game.current_turn))
    if game.other_valid_draw_claim:
        draw = game.other_valid_draw_claim.value
    else:
        draw = None
    return {
        'moves': moves,
        'draw_claim': draw
    }


def end_game(
        game: models.Game, reason: models.Conclusion):
    """Process the end of a game."""
    if reason in (
            models.Conclusion.CHECKMATE, models.Conclusion.TIME,
            models.Conclusion.RESIGN):
        if game.current_turn == models.Side.HOME:
            game.winner = models.Winner.AWAY
        else:
            game.winner = models.Winner.HOME
    else:
        game.winner = models.Winner.DRAW
    game.host.elo, game.away.elo = ratings.calculate(
        game.host.elo, game.away.elo, game.winner
    )
    game.conclusion_type = reason
    game.ended_at = datetime.datetime.now()
    game.save()
    game.host.save()
    game.away.save()
    helpers.send_game('game_end', {
        'game_state': get_game_state(game),
        'reason': reason.value
    })
    for socket in (game.host_socket_id, game.away_socket_id):
        if socket:
            connections.disconnect(
                socket, connections.DisconnectReason.GAME_OVER
            )


@helpers.event('game_state')
def game_state():
    """Send the client the entire game state.

    This only includes displayable information, use allowed_moves for working
    out what moves are allowed.
    """
    if not flask.request.context.game.started_at:
        raise helpers.RequestError(2311)
    helpers.send_user(
        'game_state', get_game_state(flask.request.context.game)
    )


@helpers.event('allowed_moves')
def allowed_moves():
    """Send a list of allowed moves.

    Only allowed if it is your turn.
    """
    game = flask.request.context.game
    if flask.request.context.side != game.current_turn:
        raise helpers.RequestError(2312)
    helpers.send_user('allowed_moves', get_allowed_moves(game))


@helpers.event('move')
def move(move_data: typing.Dict[str, typing.Any]):
    """Handle a move being made."""
    game = flask.request.context.game
    if flask.request.context.side != game.current_turn:
        raise helpers.RequestError(2312)
    if not game.game_mode.make_move(**move_data):
        raise helpers.RequestError(2313)
    game.turn_number += 1
    game.home_offering_draw = False
    game.away_offering_draw = False
    models.GameState.create(
        game=game, turn_number=int(game.turn_number),
        arrangement=game.game_state.freeze_game()
    )
    end = game.game_state.game_is_over()
    if end in (
            models.Conclusion.THREEFOLD_REPETITION,
            models.Conclusions.FIFTY_MOVE_RULE):
        game.other_valid_draw_claim = end
    else:
        game.other_valid_draw_claim = None
    game.save()
    if end in (models.Conclusion.STALEMATE, models.Conclusion.CHECKMATE):
        end_game(game, end)
    else:
        helpers.send_opponent('move', {
            'move': move_data,
            'game_state': get_game_state(game),
            'allowed_moves': get_allowed_moves(game)
        })


@helpers.event('offer_draw')
def offer_draw():
    """Handle a user offering a draw."""
    if flask.request.context.side == models.Side.HOME:
        flask.request.context.game.home_offering_draw = True
    else:
        flask.request.context.game.away_offering_draw = True
    flask.request.context.game.save()
    helpers.send_opponent('draw_offer', {})


@helpers.event('claim_draw')
def claim_draw(reason: models.Conclusion):
    """Handle a user claiming a draw."""
    ctx = flask.request.context
    if reason == models.Conclusion.AGREED_DRAW:
        if (ctx.side == models.Side.HOME) and not ctx.game.away_offering_draw:
            raise helpers.RequestError(2322)
        if (ctx.side == models.Side.AWAY) and not ctx.game.home_offering_draw:
            raise helpers.RequestError(2322)
    elif reason in (
            models.Conclusion.THREEFOLD_REPETITION,
            models.Conclusions.FIFTY_MOVE_RULE):
        if reason != ctx.game.other_valid_draw_claim:
            raise helpers.RequestError(2322)
    else:
        raise helpers.RequestError(2321)
    end_game(ctx.game, reason)


@helpers.event('resign')
def resign():
    """Handle a user resigning from the game."""
    if flask.request.context.game.current_turn != flask.request.context.side:
        # It is assumed that you can only lose on your turn.
        flask.request.context.game.turn_number += 1
        flask.request.context.game.save()
    end_game(flask.request.context.game, models.Conclusion.RESIGN)
