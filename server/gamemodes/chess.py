"""The chess gamemode."""
from __future__ import annotations

import typing

import peewee

import models

from . import gamemode


class Chess(gamemode.GameMode):
    """A gamemode for chess."""

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.game = game
        self.hypothetical_moves = None

    def layout_board(self):
        """Put the pieces on the board."""
        p = models.PieceType
        back_row = [
            p.ROOK, p.KNIGHT, p.BISHOP, p.QUEEN, p.KING, p.BISHOP, p.KNIGHT,
            p.ROOK
        ]
        for file, piece_type in enumerate(back_row):
            models.Piece.create(
                piece_type=piece_type, rank=0, file=file,
                side=models.Side.HOME, game=self.game
            )
            models.Piece.create(
                piece_type=piece_type, rank=7, file=file,
                side=models.Side.AWAY, game=self.game
            )
        for file in range(8):
            models.Piece.create(
                piece_type=p.PAWN, rank=1, file=file, side=models.Side.HOME,
                game=self.game
            )
            models.Piece.create(
                piece_type=p.PAWN, rank=6, file=file, side=models.Side.AWAY,
                game=self.game
            )

    def get_piece(self, rank: int, file: int) -> bool:
        """Get the piece on a square."""
        try:
            return models.Piece.get(
                models.Piece.file == file, models.Piece.rank == rank,
                models.Piece.game == self.game
            )
        except peewee.DoesNotExist:
            return None

    def path_is_empty(
            self, piece: models.Piece, rank: int, file: int) -> bool:
        """Check that all squares in a path are empty.

        The last square may be occupied by an enemy piece.
        """
        file_delta = file - piece.file
        rank_delta = rank - piece.rank
        steps = max(abs(file_delta), abs(rank_delta))
        file_step = file_delta // steps
        rank_step = rank_delta // steps

        # Intentionally not including the final step.
        for step in range(1, steps):
            this_file = piece.file + step * file_step
            this_rank = piece.rank + step * rank_step
            if self.get_piece(this_rank, this_file):
                return False

        victim = self.get_piece(rank, file)
        return victim.side != piece.side

    def on_board(self, rank: int, file: int) -> bool:
        """check if valid square i.e. rank and file on board"""
        return (
            rank >= 0 and rank <= 7
            and file >= 0 and file <= 7
        )

    def get_moves_in_direction(
            self, piece: models.Piece, rank_direction: int,
            file_direction: int) -> typing.Iterator[int, int]:
        """Get all moves for a unit in a direction."""
        rank, file = piece.rank, piece.file
        while True:
            rank += rank_direction
            file += file_direction
            if not self.on_board(rank, file):
                break
            target = self.get_piece(rank, file)
            if (((not target) or (target.side != piece.side))
                    and not self.hypothetical_check(piece.Side,
                    (piece, rank, file))):
                yield rank, file
            if target:
                break

    def hypothetical_check(
            self, side: models.Side,
            *moves: typing.Tuple[
                typing.Tuple[models.Piece, int, int], ...
            ]) -> bool:
        """Check if a series of moves would put a side in check."""
        if self.hypothetical_moves is not None:
            raise RuntimeError('Checkmate detection recursion detected.')
        self.hypothetical_moves = moves    # self.get_piece will observe this
        # FIXME: Observe hypothetical moves in get_piece
        king = models.Piece.get(
            models.Piece.side == side,
            models.Piece.piece_type == models.PieceType.KING,
            models.Piece.game == self.game
        )
        enemies = models.Piece.select().where(
            models.Piece.side == ~side,
            models.Piece.game == self.game
        )
        for enemy in enemies:
            check = self.validate_move(
                enemy.file, enemy.rank, king.file, king.rank,
                check_allowed=True
            )
            if check:
                self.hypothetical_moves = None
                return True
        self.hypothetical_moves = None
        return False

    def validate_pawn_move(
            self, pawn: models.Piece, rank: int, file: int) -> bool:
        """Validate a pawn's move."""
        absolute_file_delta = abs(file - pawn.file)
        relative_rank_delta = pawn.side.forwards * (rank - pawn.rank)
        if relative_rank_delta == 0:
            return False
        elif relative_rank_delta == 1:
            if absolute_file_delta == 0:
                return not self.get_piece(rank, file)
            elif absolute_file_delta == 1:
                victim = self.get_piece(rank, file)
                en_passant_pawn = self.get_piece(pawn.rank, file)
                en_passant_valid = (
                    en_passant_pawn and en_passant_pawn.side != pawn.side
                    and en_passant_pawn.first_move_last_turn
                    and pawn.rank == (4 if pawn.side == models.Side.HOME else 3)
                )
                return (victim and victim.side != pawn.side) or en_passant_valid
            else:
                return False
        elif relative_rank_delta == 2:
            if absolute_file_delta:
                return False
            if pawn.has_moved:
                return False
            return not bool(
                self.get_piece(rank, file)
                or self.get_piece(rank, file - pawn.side.forwards)
            )
        else:
            return False

    def get_pawn_moves(self, pawn: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a pawn."""
        options = ((1, 0), (2, 0), (1, -1), (1, 1))
        for absolute_rank_delta, file_delta in options:
            rank = pawn.rank + absolute_rank_delta * pawn.side.forwards
            file = pawn.file + file_delta
            if (self.on_board(rank, file)
                    and self.validate_pawn_move(pawn, rank, file)
                    and self.hypothetical_check(pawn.side, (pawn, rank, file))):
                yield rank, file

    def validate_rook_move(
            self, rook: models.Piece, rank: int, file: int) -> bool:
        """Validate a rook's move."""
        file_delta = file - rook.file
        rank_delta = rank - rook.file
        if file_delta and rank_delta:
            return False
        return self.path_is_empty(rook, rank, file)

    def get_rook_moves(self, rook: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a rook."""
        for direction in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            for move in self.get_moves_in_direction(rook, *direction):
                yield move

    def validate_knight_move(
            self, knight: models.Piece, rank: int, file: int) -> bool:
        """Validate a knight's move."""
        absolute_file_delta = abs(file - knight.file)
        absolute_rank_delta = abs(rank - knight.rank)
        if (absolute_file_delta, absolute_rank_delta) not in ((1, 2), (2, 1)):
            return False
        victim = self.get_piece(rank, file)
        return (not victim) or (victim.side != knight.side)

    def get_knight_moves(
            self, knight: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a knight."""
        for rank_absolute, file_absolute in ((1, 2), (2, 1)):
            for rank_direction in (-1, 1):
                for file_direction in (-1, 1):
                    rank = knight.rank + rank_absolute * rank_direction
                    file = knight.file + file_absolute * file_direction
                    victim = self.get_piece(rank, file)
                    if (not victim) or (victim.side != knight.side):
                        if not self.hypothetical_check(knight, rank, file):
                            yield rank, file

    def validate_bishop_move(
            self, bishop: models.Piece, rank: int, file: int) -> bool:
        """Validate a bishop's move."""
        absolute_file_delta = abs(file - bishop.file)
        absolute_rank_delta = abs(rank - bishop.rank)
        if absolute_file_delta != absolute_rank_delta:
            return False
        return self.path_is_empty(bishop, rank, file)

    def get_bishop_moves(
            self, bishop: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a bishop."""
        for direction in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            for move in self.get_moves_in_direction(bishop, *direction):
                yield move

    def validate_queen_move(
            self, queen: models.Piece, rank: int, file: int) -> bool:
        """Validate a queen's move."""
        absolute_file_delta = abs(file - queen.file)
        absolute_rank_delta = abs(rank - queen.rank)
        bishops_move = absolute_file_delta == absolute_rank_delta
        rooks_move = bool(absolute_file_delta) ^ bool(absolute_rank_delta)
        if not (bishops_move or rooks_move):
            return False
        return self.path_is_empty(queen, rank, file)

    def get_queen_moves(
            self, queen: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a queen."""
        for file_direction in (-1, 0, 1):
            for rank_direction in (-1, 0, 1):
                direction = (rank_direction, file_direction)
                if direction == (0, 0):
                    continue
                for move in self.get_moves_in_direction(queen, *direction):
                    yield move

    def validate_king_move(
            self, king: models.Piece, rank: int, file: int) -> bool:
        """Validate a king's move."""
        absolute_file_delta = abs(file - king.file)
        absolute_rank_delta = abs(rank - king.rank)
        if (not absolute_rank_delta) and not king.has_moved:
            if file == 2:
                rook_start = 0
                rook_end = 3
                empty_files = (1, 2, 3)
            elif file == 6:
                rook_start = 7
                rook_end = 5
                empty_files = (5, 6)
            else:
                return False
            rook = self.get_piece(rank, rook_start)
            if (not rook) or rook.has_moved:
                return False
            for empty_file in empty_files:
                if not self.get_piece(rank, empty_file):
                    return False
            return not self.hypothetical_check(
                king.side, (king, rank, file), (rook, rank, rook_end)
            )
        if (absolute_file_delta > 1) or (absolute_rank_delta > 1):
            return False
        return True


    def get_king_moves(self, king: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a king."""
        for file_direction in (-1, 0, 1):
            for rank_direction in (-1, 0, 1):
                direction = (rank_direction, file_direction)
                if direction == (0, 0):
                    continue
                rank = king.rank + rank_direction
                file = king.file + file_direction
                if not self.on_board(file, rank):
                    continue
                victim = self.get_piece(rank, file)
                if (((not victim) or (victim.side != king.side))
                        and not self.hypothetical_check(king.side,
                        (king, rank, file))):
                    yield rank, file
        if not king.has_moved:
            for file_direction in (-2, 2):
                file = king.file + file_direction
                self.validate_king_move(king, king.rank, file)

    def validate_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int, check_allowed: bool = False) -> bool:
        """Validate a move."""
        if start_file == end_file and start_rank == end_rank:
            return False
        piece = self.get_piece(start_rank, start_file)
        if not piece:
            return False
        if not self.on_board(end_rank, end_file):
            return False
        validators = {
            models.PieceType.PAWN: self.validate_pawn_move,
            models.PieceType.ROOK: self.validate_rook_move,
            models.PieceType.KNIGHT: self.validate_knight_move,
            models.PieceType.BISHOP: self.validate_bishop_move,
            models.PieceType.QUEEN: self.validate_queen_move,
            models.PieceType.KING: self.validate_king_move
        }
        if not validators[piece.piece_type](piece, end_rank, end_file):
            return False
        return check_allowed or not self.hypothetical_check(
            piece.side, (piece, end_rank, end_file)
        )

    def possible_moves(self, side: models.Side) -> typing.Iterator[
            typing.Tuple[models.Piece, int, int]]:
        """Get all possible moves for a side."""
        pieces = models.Piece.select().where(
            models.Piece.side == side,
            models.Piece.game == self.game
        )
        move_generators = {
            models.PieceType.PAWN: self.get_pawn_moves,
            models.PieceType.ROOK: self.get_rook_moves,
            models.PieceType.KNIGHT: self.get_knight_moves,
            models.PieceType.BISHOP: self.get_bishop_moves,
            models.PieceType.QUEEN: self.get_queen_moves,
            models.PieceType.KING: self.get_king_moves
        }
        for piece in pieces:
            for rank, file in move_generators[piece.piece_type](piece):
                if not self.hypothetical_check(side, (piece, rank, file)):
                    yield piece, rank, file

    def game_is_over(self) -> models.Conclusion:
        """Check if the game has been won or tied.

        If the return value is checkmate, the player whos turn it currently
        is is in checkmate. This method must be called after the GameState
        for the current turn has been created. Note that a return of
        THREEFOLD_REPETITION or FIFTY_MOVE_RULE should not immediately end the
        game - rather, at least one player must claim the draw.
        """
        current_state = models.GameState.get(
            models.GameState.game == self.game,
            models.GameState.turn_number == int(self.game.turn_number)
        )
        identical_states = models.GameState.select().where(
            models.GameState.game == self.game,
            models.GameState.arrangement == current_state.arrangement
        )
        if len(list(identical_states)) >= 3:
            return models.Conclusion.THREEFOLD_REPETITION
        if self.game.turn_number >= self.game.last_kill_or_pawn_move + 50:
            return models.Conclusion.FIFTY_MOVE_RULE
        moves_available = list(self.possible_moves(self.game.current_turn))
        if moves_available:
            return models.Conclusion.GAME_NOT_COMPLETE
        if self.hypothetical_check(self.game.current_turn):
            return models.Conclusion.CHECKMATE
        return models.Conclusion.STALEMATE

    def freeze_game(self) -> str:
        """Store a snapshot of a game as a string."""
        pieces = models.Piece.select().where(
            models.Piece.game == self.game
        ).order_by(
            models.Piece.rank, models.Piece.file
        )
        arrangement = ''
        castleable_rooks = []
        for side in (self.game.current_turn, ~self.game.current_turn):
            king = models.Piece.get(
                models.Piece.game == self.game,
                models.Piece.side == side,
                models.Piece.piece_type == models.PieceType.KING
            )
            for rook, _king_rank in self.get_allowed_castling(king):
                castleable_rooks.append(rook.id)
        for piece in pieces:
            if piece.piece_type == models.PieceType.KNIGHT:
                abbrev = 'n'
            else:
                abbrev = piece.piece_type.name[0]
            if piece.side == models.Side.HOME:
                abbrev = abbrev.upper()
            arrangement += (
                abbrev + str(models.Piece.rank) + str(models.Piece.file)
            )
            if piece.piece_type == models.PieceType.PAWN:
                if piece.first_move_last_turn:
                    arrangement += 'X'
            elif piece.piece_type == models.PieceType.ROOK:
                if piece.id in castleable_rooks:
                    arrangement += 'X'
        return arrangement
