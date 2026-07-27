# SFA Bot  Architecture & Implementation Plan

## Context

SFA Bot is a single-server Discord bot for managing an American Football league played on Roblox. One guild, no website, no billing, no Kubernetes  just a Discord bot, PostgreSQL, and Redis in Docker Compose.

The league format is unique: 32 teams across 4 fluid divisions, 4 group stages per season (3 games each = 12 games per team total), a Standings Points (SP) system that determines playoff qualification, and promotion/relegation between stages driven by a predetermined formula.

Input documents:
- `sfa-bot-plans/season-format.md`  full season format specification
- `sfa-bot-plans/command-wishlist.md`  22 commands with permission levels

---

## Stack

| Concern | Choice | Why |
|---|---|---|
| Database | PostgreSQL 18.4 | Robust, well-known, async support |
| Cache / cooldowns | Redis 8.8.1 | Lightweight, TTL-based expiry for media ping cooldowns |
| Bot library | discord.py `Bot` | Single guild  no sharding needed |
| Data validation | msgspec + structhook | Fast, validates at the boundary |
| Logging | structlog | Structured, colored console output for dev |
| Migrations | Alembic + SQLAlchemy | DDL generation only  models are never imported at runtime |
| Deployment | Docker Compose | 3 containers: postgres, redis, bot |

---

## Configuration

Settings are stored in a JSON file (`config.json`) at the project root. For a single-server bot, a database table for settings is overkill. The JSON file is loaded at startup into a frozen msgspec struct:

```python
# sfa_bot/config.py
from msgspec import Struct, field


class GuildConfig(Struct, frozen=True):
    guild_id: int
    # Role IDs
    commissioner_role_id: int
    vice_role_id: int
    staff_stats_role_id: int
    staff_media_role_id: int
    staff_mods_role_id: int
    staff_justice_role_id: int
    team_owner_role_id: int
    premium_booster_role_id: int = 0
    premium_t1_role_id: int = 0
    premium_t2_role_id: int = 0
    premium_t3_role_id: int = 0
    # Channel IDs
    scheduling_channel_id: int = 0
    gametimes_channel_id: int = 0
    lfp_channel_id: int = 0
    media_channel_ids: list[int] = field(default_factory=list)
    # Misc
    logging_webhook_url: str = ""


def load_config(path: str = "config.json") -> GuildConfig:
    import json

    with open(path) as f:
        return msgspec.convert(orjson.load(f.read()), GuildConfig)
```

Secrets (tokens, passwords) stay in `.env`. The JSON config is for Discord snowflakes that change per-server setup. Role and channel IDs are configured once when setting up the bot for the guild.

---

## Database Schema

Full schema in `sfa.dbml`.

### Design Conventions

- **Enums stored as integers**  no PostgreSQL enum types. Every enum has a comment mapping int → meaning.
- **Soft delete**  `is_active` boolean flag. Never hard-delete history rows.
- **Insert-only history**  `team_owner` tracks appointments/unappointments with both timestamps. `contract` rows are deactivated via `is_active`; termination metadata is stored inline.
- **Filtered unique indexes**  `WHERE is_active = true` for one-active-row-per-entity constraints.
- **Optimistic concurrency**  `version` column on `season` and `game` tables. Update with `WHERE version = $expected`, return 409 on mismatch.
- **Single guild**  no `guild_id` column on any table. The bot serves exactly one server.

### Tables (12 total)

| Table | Purpose | Key columns (beyond PK + timestamps) |
|---|---|---|
| `player` | Discord user + Roblox linking | `snowflake` (PK), `roblox_id` |
| `team` | Franchises with division tracking | `role_snowflake`, `role_name`, `division`, `subdivision`, `gsp`, `is_active` |
| `coach` | Person-based coaching staff | `role_snowflake`, `role_name`, `acronym`, `sort_index` |
| `team_owner` | Ownership change log | `player_snowflake` FK, `team_id` FK, `appointed_at`, `unappointed_at` |
| `season` | Season & stage tracking | `season_number`, `current_stage` (1-5), `is_playoffs`, `version` |
| `team_season_stage` | Per-stage placement snapshot | `season_id` FK, `team_id` FK, `stage`, `division`, `subdivision`, `gsp`, `is_play_in`, `is_auto_qualified`, `is_champion` |
| `game` | Match results | `home_team_id`/`away_team_id` FK, scores, `stage`, `division`, `subdivision`, `week`, `version` |
| `player_stat` | Per-player per-game position stats | `game_id` FK, `roblox_id`, `player_snowflake` FK, position JSONB columns |
| `contract` | Active roster record | `player_snowflake` FK, `team_id` FK, `amount`, `length`, `length_type`, `is_active` |
| `award` | Custom awards | `season_id` FK (nullable for HOF), `name`, `category`, `description`, `role_snowflake` |
| `award_assignment` | Awards granted | `award_id` FK, `player_snowflake` FK, `team_id` FK |
| `player_sanction` | Suspensions + blacklists | `player_snowflake` FK, `sanction_type` (0-1), `sanctioned_until`, `banned_until`, `is_active` |

### Enum Reference

**Division**: 1=D1, 2=D2, 3=D3, 4=D4

**GameStage**: 1=GROUP_1, 2=GROUP_2, 3=GROUP_3, 4=GROUP_4, 5=GROUP_5, 6=PLAYOFFS_R1, 7=PLAYOFFS_QF, 8=PLAYOFFS_SF, 9=PLAYOFFS_FINAL

**GroupStandingPosition**: 1=FIRST (+15 SP), 2=SECOND (+10), 3=THIRD (+5), 4=FOURTH (+0)

**SanctionType**: 0=SUSPENSION, 1=TEAM_OWNER_BLACKLIST

**AppointmentTier**: 0=BOOSTER, 1=DONATOR_T1, 2=DONATOR_T2, 3=DONATOR_T3

---

## Project Structure

```
sfa-bot/
├── sfa_bot/                    # Discord bot package
│   ├── __init__.py
│
├── migrations/                 # Alembic (DDL only  never imported at runtime)
│   ├── models/                 # Mirror of sfa_bot/db/models/ for autogenerate
│   │   └── ...(same 12 files)
│   └── versions/
│
├── config.json                 # Guild-specific role & channel IDs
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

Each cog delegates to its service layer. Services contain the actual logic and database queries. Cogs handle Discord interaction concerns: deferring, embeds, permission checks. This keeps cogs thin and services testable.

---

## Key Algorithms

### 1. Group Stage Schedule Generation

**Setup (once per season):**
1. 32 teams with initial seeds
2. Assign divisions: D1 (seeds 1-8), D2 (9-16), D3 (17-24), D4 (25-32)
3. Subdivide: top 4 seeds → A, bottom 4 → B within each division
4. Write initial rows to `team_season_stage` for stage 1

**Each stage (4 per season, 3 weeks each):**
- 8 groups total (2 groups per division × 4 divisions)
- Groups formed by static seed formula within each division:
  - Group 1: seeds 1, 4, 5, 8
  - Group 2: seeds 2, 3, 6, 7
- Each group plays a 3-game round-robin (circle method):
  - Week 1: (1 vs 4), (2 vs 3)
  - Week 2: (1 vs 3), (2 vs 4)
  - Week 3: (1 vs 2), (3 vs 4)
- Home/away alternates by seed parity
- 8 groups × 3 games = 24 games per stage, 96 per season

### 2. Standings Points (SP) Calculation

SP determines playoff qualification. It is calculated per-game and summed per-stage. **SP is computed on-the-fly from game scores — it is not stored in the database.** The `team_season_stage.gsp` column records the Group Standing Position after stage completion, which is the only persisted SP-related value.

**Base SP by division:**
| Division | Win SP | Loss SP | Minimum SP per Stage |
|---|---|---|---|
| D1 | 15 | 8 | 24 |
| D2 | 12 | 6 | 18 |
| D3 | 9 | 4 | 12 |
| D4 | 6 | 3 | 9 |

**Margin bonus (on top of base SP):**
| Point Differential | Winner Bonus | Loser Bonus |
|---|---|---|
| ±0 (FFW/FFL) | +3 (FFW) / +0 (FFL) | +0 |
| ±0 (tie) | +2 | +2 |
| ±0 (double FFL) | +0 | +0 |
| ±1–14 | +3 | +2 |
| ±15–34 | +4 | +1 |
| ±35+ (mercy rule) | +6 | +0 |

**GSP bonus (awarded after stage completion):**
| GSP | Bonus SP |
|---|---|
| 1st | +15 |
| 2nd | +10 |
| 3rd | +5 |
| 4th | +0 |

**Per-game SP = base_SP + margin_bonus.**
**Per-stage SP = sum(per-game SP) + GSP_bonus, clamped to minimum.**

**Group standings** (for GSP determination) are sorted by: Record (W-L) → Point Differential → Points For. SP is NOT used to determine group standings  it's only for playoff qualification.

### 3. Promotion/Relegation

After each stage, teams move divisions based on their GSP. The movement is looked up from static tables  not increment/decrement arithmetic, which allows "double" jumps.

**Stage 1 (aggressive shuffling to balance divisions):**
| Div | GSP 1 | GSP 2 | GSP 3 | GSP 4 |
|---|---|---|---|---|
| D1 | Stay (D1A) | Demote (D2A) | Demote (D2B) | Double Demote (D3B) |
| D2 | Promote (D1B) | Promote (D1A) | Demote (D3A) | Double Demote (D4B) |
| D3 | Double Promote (D1A) | Promote (D2A) | Stay (D3B) | Demote (D4A) |
| D4 | Double Promote (D2A) | Promote (D3A) | Stay (D4B) | Stay (D4B) |

**Stages 2-4 (stable  same table each stage):**
| Div | GSP 1 | GSP 2 | GSP 3 | GSP 4 |
|---|---|---|---|---|
| D1 | Stay (D1A) | Stay (D1B) | Demote (D2B) | Demote (D3B) |
| D2 | Promote (D1B) | Promote (D2A) | Stay (D3A) | Demote (D4A) |
| D3 | Promote (D2A) | Stay (D3A) | Demote (D4B) | Demote (D4B) |
| D4 | Promote (D3A) | Promote (D4A) | Stay (D4B) | Stay (D4B) |

After all movements are applied, re-seed within each division by total SP (1-8), then subdivide A/B (top 4 → A, bottom 4 → B). New `team_season_stage` rows are written for the next stage.

### 4. Tiered Appointment Probability

For `/appoint`: candidates are selected with tier-based priority. "Equal chance for all non-boosters/non-donators and boosters/donators of the same tier, then priority: Booster < Donator T1 < Donator T2 < Donator T3."

```python
def select_appointee(candidates: list[tuple[int, int]]) -> int:
    """candidates: list of (player_snowflake, highest_tier).
    Only candidates at the highest present tier are eligible.
    Within that tier: equal random probability."""
    from collections import defaultdict
    import random

    tier_groups = defaultdict(list)
    for snowflake, tier in candidates:
        tier_groups[tier].append(snowflake)

    highest_tier = max(tier_groups.keys())
    return random.choice(tier_groups[highest_tier])
```

In practice: if any Donator T3 is a candidate, one of them is selected (100% probability pool). When all T3 candidates are appointed, T2 becomes the eligible pool, and so on. Non-donators only get a chance when no boosted/donator candidates exist.

---

## Permission System

Role-based using Discord role IDs from `config.json`. Not a bitmask  each permission level is a simple role check:

```python
# sfa_bot/utils/checks.py


def has_role(member: discord.Member, role_id: int) -> bool:
    return any(role.id == role_id for role in member.roles)


def is_commissioner(member: discord.Member) -> bool:
    cfg = get_config()
    return has_role(member, cfg.commissioner_role_id) or has_role(member, cfg.vice_role_id)


def is_commissioner_only(member: discord.Member) -> bool:
    cfg = get_config()
    return has_role(member, cfg.commissioner_role_id)


def is_staff(member: discord.Member, subgroup: str) -> bool:
    cfg = get_config()
    subgroup_roles = {
        "STATS": cfg.staff_stats_role_id,
        "MEDIA": cfg.staff_media_role_id,
        "MODS": cfg.staff_mods_role_id,
        "JUSTICE": cfg.staff_justice_role_id,
    }
    return is_commissioner(member) or has_role(member, subgroup_roles[subgroup])


def is_team_owner(member: discord.Member) -> bool:
    cfg = get_config()
    return has_role(member, cfg.team_owner_role_id)


def is_premium(member: discord.Member) -> bool:
    cfg = get_config()
    return any(
        has_role(member, rid)
        for rid in [cfg.premium_booster_role_id, cfg.premium_t1_role_id, cfg.premium_t2_role_id, cfg.premium_t3_role_id]
        if rid
    )
```

Commissioner always inherits all staff subgroup permissions. Vice inherits commissioner permissions except for `/forceappoint` (commissioner-only).

Commands are synced guild-scoped for instant registration (no 1-hour global sync delay):
```python
await self.tree.sync(guild=discord.Object(id=config.guild_id))
```

---

## Command Gap Analysis

The current wishlist has 22 commands. Several are missing that a functional league would need:

| Gap | Why Needed | Suggested |
|---|---|---|
| Game reporting | No way to submit scores/stats | `/reportgame` with score modal |
| Sign/release | Core roster management | `/sign`, `/release` |
| Schedule viewing | Teams need to see upcoming games | `/schedule` or `/mygames` |
| Standings viewing | See league table/SP | `/standings` |

These should be proposed to the league operator before or during implementation.

---

## Docker Compose Setup

```yaml
services:
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: sfa
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: sfa
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sfa"]
      interval: 5s

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  bot:
    build: .
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://sfa:${POSTGRES_PASSWORD}@postgres:5432/sfa
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      DISCORD_TOKEN: ${DISCORD_TOKEN}
    volumes:
      - ./config.json:/app/config.json:ro
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

Single connection pool direct to PostgreSQL  no PgBouncer needed at this scale.

---

## Verification Plan

1. **Schema**: `alembic upgrade head` on fresh PostgreSQL  all 12 tables create, indexes exist, FKs are valid
2. **Bot startup**: `docker compose up`  bot connects to Discord, guild commands appear instantly
3. **Commands**: Run each of the 22 commands in a test Discord server  verify correct permission gating, DB writes succeed
4. **Schedule**: 32 test teams → generate schedule → verify 8 groups of 4, 3 games per team per stage, no duplicate matchups within a group
5. **SP calculation**: Report games across all margin scenarios (close, blowout, forfeit, tie, mercy rule)  verify SP values match the formula
6. **Promotion/relegation**: Complete a full stage → verify each team's new division matches the static lookup table
7. **Full season**: Simulate 4 stages + playoffs → verify cumulative SP, playoff qualification, season close
