import datetime

from structhook import DotDict, field

from .award_assignment import AwardAssignment
from .base import DatabaseModel
from .contract import Contract
from .game import Game
from .player_sanction import PlayerSanction
from .player_stat import PlayerStat
from .team_owner_history import TeamOwnerHistory

__all__ = [
    "Player",
]


class Player(DatabaseModel):
    """Discord user linked to a Roblox account."""

    snowflake: int
    roblox_id: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

    team_owner_history: DotDict[int, TeamOwnerHistory] = field(default_factory=DotDict, exclude=True)
    award_assignments: DotDict[int, AwardAssignment] = field(default_factory=DotDict, exclude=True)
    contracts: DotDict[int, Contract] = field(default_factory=DotDict, exclude=True)
    sanctions: DotDict[int, PlayerSanction] = field(default_factory=DotDict, exclude=True)
    moderated_sanctions: DotDict[int, PlayerSanction] = field(default_factory=DotDict, exclude=True)
    reported_games: DotDict[int, Game] = field(default_factory=DotDict, exclude=True)
    approved_games: DotDict[int, Game] = field(default_factory=DotDict, exclude=True)
    stats: DotDict[int, PlayerStat] = field(default_factory=DotDict, exclude=True)
