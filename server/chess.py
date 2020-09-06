"""The chess gamemode."""
import models

import peewee


class Chess:
    """A gamemode for chess."""

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
            return bool(
                self.get_piece(rank, file)
                or self.get_piece(rank, file - pawn.side.forwards)
            )
        else:
            return False

    def validate_rook_move(
            self, rook: models.Piece, rank: int, file: int) -> bool:
        """Validate a rook's move."""
        rank_delta = rank - rook.rank
        file_delta = file - rook.rank
        if rank_delta and file_delta:
            return False
        return self.path_is_empty(rook, rank, file)

    def validate_knight_move(
            self, knight: models.Piece, rank: int, file: int) -> bool:
        """Validate a knight's move."""
        absolute_rank_delta = abs(rank - knight.rank)
        absolute_file_delta = abs(file - knight.file)
        if (absolute_rank_delta, absolute_file_delta) not in ((1, 2), (2, 1)):
            return False
        victim = self.get_piece(rank, file)
        return (not victim) or (victim.side != knight.side)

    def validate_bishop_move(
            self, bishop: models.Piece, rank: int, file: int) -> bool:
        """Validate a bishop's move."""
        absolute_rank_delta = abs(rank - bishop.rank)
        absolute_file_delta = abs(file - bishop.file)
        if absolute_rank_delta != absolute_file_delta:
            return False
        return self.path_is_empty(bishop, rank, file)

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

    def validate_king_move(
            self, king: models.Piece, rank: int, file: int) -> bool:
        """Validate a king's move."""
        absolute_rank_delta = abs(rank - king.rank)
        absolute_file_delta = abs(file - king.file)
        if (absolute_rank_delta > 1) or (absolute_file_delta > 1):
            return False
        # TODO: Handle castling.
        return True

    def validate_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int) -> bool:
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
        # TODO: Check for moving into checkmate.
        return True
