"""Calculate ELO ratings."""
import typing

from .config import ELO_K_FACTOR
from .models import Winner


def transformed_rating(elo: int) -> int:
    """Calculate "transformed rating" for easier calculations."""
    return 10 ** (elo / 400)


def updated_rating(old: int, expected: int, actual: int) -> int:
    """Calculate the updated rating for a single user."""
    return round(old + ELO_K_FACTOR * (actual - expected))


def host_result_value(winner: Winner) -> float:
    """Get the "actual" result for the host."""
    if winner == Winner.HOME:
        return 1
    if winner == Winner.AWAY:
        return 0
    return 0.5


def calculate(
        host_elo: int, away_elo: int,
        winner: Winner) -> typing.Tuple[int, int]:
    """Calculate the updated ELO after a match."""
    host_transformed = transformed_rating(host_elo)
    away_transformed = transformed_rating(away_elo)
    total_transformed = host_transformed + away_transformed
    host_expected = host_transformed / total_transformed
    away_expected = away_transformed / total_transformed
    host_actual = host_result_value(winner)
    away_actual = 1 - host_actual
    host_updated = updated_rating(host_elo, host_expected, host_actual)
    away_updated = updated_rating(away_elo, away_expected, away_actual)
    return host_updated, away_updated
