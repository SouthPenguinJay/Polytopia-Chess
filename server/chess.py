"""The chess gamemode."""
import typing

import models

import peewee


Move = typing.Tuple[models.Piece, int, int]


class Chess:
    """A gamemode for chess."""

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.game == game

    def layout_board(self):
        """Put the pieces on the board."""
        p = models.PieceType
        back_row = [
            p.ROOK, p.KNIGHT, p.BISHOP, p.QUEEN, p.KING, p.BISHOP, p.KNIGHT,
            p.ROOK
        ]
        for rank, piece_type in enumerate(back_row):
            models.Piece.create(
                piece_type=piece_type, file=1, rank=rank,
                side=models.Side.HOME, game=self.game
            )
            models.Piece.create(
                piece_type=piece_type, file=6, rank=rank,
                side=models.Side.AWAY, game=self.game
            )
        for rank in range(8):
            models.Piece.create(
                piece_type=p.PAWN, file=0, rank=rank, side=models.SIDE.HOME,
                game=self.game
            )
            models.Piece.create(
                piece_type=p.PAWN, file=7, rank=rank, side=models.SIDE.AWAY,
                game=self.game
            )

    def get_piece(self, rank: int, file: int) -> bool:
        """Get the piece on a square."""
        try:
            return models.Piece.get(
                models.Piece.rank == rank, models.Piece.file == file,
                models.Piece.game == self.game
            )
        except peewee.NotFound:
            return None

    def path_is_empty(
            self, piece: models.Piece, rank: int, file: int) -> bool:
        """Check that all squares in a path are empty.

        The last square may be occupied by an enemy piece.
        """
        rank_delta = rank - piece.rank
        file_delta = file - piece.file
        assert abs(rank_delta) == abs(file_delta), 'Path must be straight.'
        steps = max(abs(rank_delta), abs(file_delta))
        rank_step = rank_delta // steps
        file_step = file_delta // steps

        # Intentionally not including the final step.
        for step in range(1, steps):
            this_rank = piece.rank + step * rank_step
            this_file = piece.file + step * file_step
            if self.get_piece(this_rank, this_file):
                return False

        victim = self.get_piece(rank, file)
        return victim.side != piece.side

    def get_moves_in_direction(
            self, piece: models.Piece, rank_direction: int,
            file_direction: int) -> typing.Iterator[int, int]:
        """Get all moves for a unit in a direction."""
        rank, file = piece.rank, piece.file
        while True:
            rank += rank_direction
            file += file_direction
            target = self.get_piece(rank, file)
            if target:
                if target.side == piece.side:
                    break
                yield rank, file
                break
            else:
                yield rank, file

    def hypothetical_check(
            self, side: models.Side, *moves: typing.Tuple[Move, ...]) -> bool:
        """Check if a series of moves would put a side in check."""
        if self.hypothetical_moves is None:
            raise RuntimeError('Checkmate detection recursion detected.')
        self.hypothetical_moves = moves    # self.get_piece will observe this
        king = models.Piece.get(
            models.Piece.side == side,
            models.Piece.piece_type == models.PieceType.KING,
            models.Piece.game == self.game
        )
        enemies = models.Piece.select().where(
            models.Piece.side == side,
            models.Piece.game == self.game
        )
        for enemy in enemies:
            check = self.validate_move(
                enemy.rank, enemy.file, king.rank, king.file,
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
        absolute_rank_delta = abs(rank - pawn.rank)
        relative_file_delta = pawn.side.forwards * (file - pawn.file)
        if relative_file_delta == 0:
            return False
        elif relative_file_delta == 1:
            if absolute_rank_delta == 0:
                return not self.get_piece(rank, file)
            elif absolute_rank_delta == 1:
                victim = self.get_piece(rank, file)
                return victim and victim.side != pawn.side
            else:
                return False
        elif relative_file_delta == 2:
            if absolute_rank_delta:
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
        in_front = self.get_piece(pawn.rank, pawn.file + pawn.side.forwards)
        if not in_front:
            yield pawn.rank, pawn.file + pawn.side.forwards
        if (not pawn.has_moved) and not in_front:
            two_in_front = self.get_piece(
                pawn.rank, pawn.file + pawn.side.forwards * 2
            )
            if two_in_front:
                yield pawn.rank, pawn.file + pawn.side.forwards * 2
        for direction in (-1, 1):
            rank = pawn.rank + direction
            file = pawn.file + pawn.side.forwards
            target = self.get_piece(rank.file)
            if not target:
                en_passant_pawn = self.get_piece(rank, pawn.file)
                en_passant_valid = (
                    en_passant_pawn and en_passant_pawn.side != pawn.side
                    and en_passant_pawn.first_move_last_turn
                )
                if en_passant_valid:
                    yield (rank, file)
            if target and target.side != pawn.side:
                yield rank, file

    def validate_rook_move(
            self, rook: models.Piece, rank: int, file: int) -> bool:
        """Validate a rook's move."""
        rank_delta = rank - rook.rank
        file_delta = file - rook.rank
        if rank_delta and file_delta:
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
        absolute_rank_delta = abs(rank - knight.rank)
        absolute_file_delta = abs(file - knight.file)
        if (absolute_rank_delta, absolute_file_delta) not in ((1, 2), (2, 1)):
            return False
        victim = self.get_piece(rank, file)
        return (not victim) or (victim.side != knight.side)

    def get_knight_moves(
            self, knight: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a knight."""
        for file_absolute, rank_absolute in ((1, 2), (2, 1)):
            for file_direction in (-1, 1):
                for rank_direction in (-1, 1):
                    file = knight.file + file_absolute * file_direction
                    rank = knight.rank + rank_absolute * rank_direction
                    victim = self.get_piece(rank, file)
                    if (not victim) or (victim.side != knight.side):
                        yield (rank, file)

    def validate_bishop_move(
            self, bishop: models.Piece, rank: int, file: int) -> bool:
        """Validate a bishop's move."""
        absolute_rank_delta = abs(rank - bishop.rank)
        absolute_file_delta = abs(file - bishop.file)
        if absolute_rank_delta != absolute_file_delta:
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
        absolute_rank_delta = abs(rank - queen.rank)
        absolute_file_delta = abs(file - queen.file)
        bishops_move = absolute_rank_delta == absolute_file_delta
        rooks_move = bool(absolute_rank_delta) ^ bool(absolute_file_delta)
        if not (bishops_move or rooks_move):
            return False
        return self.path_is_empty(queen, rank, file)

    def get_queen_moves(
            self, queen: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a queen."""
        for rank_direction in (-1, 0, 1):
            for file_direction in (-1, 0, 1):
                direction = (rank_direction, file_direction)
                if direction == (0, 0):
                    continue
                for move in self.get_moves_in_direction(queen, *direction):
                    yield move

    def validate_king_move(
            self, king: models.Piece, rank: int, file: int) -> bool:
        """Validate a king's move."""
        absolute_rank_delta = abs(rank - king.rank)
        absolute_file_delta = abs(file - king.file)
        if (not absolute_file_delta) and not king.has_moved:
            if rank == 2:
                rook_start = 0
                rook_end = 3
                empty_ranks = (1, 2, 3)
            elif rank == 6:
                rook_start = 7
                rook_end = 5
                empty_ranks = (5, 6)
            else:
                return False
            rook = self.get_piece(rook_start, file)
            if (not rook) or rook.has_moved:
                return False
            for empty_rank in empty_ranks:
                if not self.get_piece(empty_rank, file):
                    return False
            return not self.hypothetical_check(
                king.side, (king, rank, file), (rook, rook_end, file)
            )
        if (absolute_rank_delta > 1) or (absolute_file_delta > 1):
            return False
        return True

    def get_king_moves(self, king: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a king."""
        for rank_direction in (-1, 0, 1):
            for file_direction in (-1, 0, 1):
                direction = (rank_direction, file_direction)
                if direction == (0, 0):
                    continue
                file = king.file + file_direction
                rank = king.rank + rank_direction
                victim = self.get_piece(rank, file)
                if (not victim) or (victim.side != king.side):
                    yield rank, file
        if not king.has_moved:
            options = ((0, 3, 2, (1, 2, 3)), (7, 5, 6, (5, 6)))
            for rook_start, rook_end, king_end, empty_ranks in options:
                rook = self.get_piece(rook_start, king.file)
                if (not rook) or rook.has_moved:
                    continue
                empty_squares_empty = True
                for empty_rank in empty_ranks:
                    if not self.get_piece(empty_rank, file):
                        empty_squares_empty = False
                        break
                if not empty_squares_empty:
                    continue
                valid = not self.hypothetical_check(
                    king.side, (king, king_end, king.file),
                    (rook, rook_end, king.file)
                )
                if valid:
                    yield king_end, king.file

    def validate_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int, check_allowed: bool = False) -> bool:
        """Validate a move."""
        if start_rank == end_rank and start_file == end_file:
            return False
        out_of_board = (
            (end_rank < 0) or (end_rank > 7)
            or (end_file < 0) or (end_rank > 7)
        )
        if out_of_board:
            return False
        piece = self.get_piece(start_rank, start_file)
        if not piece:
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
        return check_allowed or not self.hypothetical_check(piece.side)

    def possible_moves(self, side: models.Side) -> typing.Iterator[Move]:
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

    def check_checkmate(self, side: models.Side) -> bool:
        """Check if the game has been won by checkmate."""
        if not self.hypothetical_check(side):
            return False
        return bool(list(self.possible_moves(side)))

    def check_stalemate(self) -> bool:
        """Check if the game has ended in stalemate.

        This method assumes that it is not checkmate.
        """
        return bool(list(self.possible_moves(self.game.current_turn)))
