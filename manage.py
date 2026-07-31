"""SFA Bot management script.

Usage: python manage.py <command> [target]

Commands:
  start [infra|bot]   Start services (all when no target given).
  stop [infra|bot]    Stop services (all when no target given).
  down                Tear down all services, keep volumes.
  remove              Tear down all services and delete volumes.
  migrate             Run Alembic migrations.

Migrate sub-commands:
  python manage.py migrate upgrade              Apply pending migrations.
  python manage.py migrate generate "message"   Autogenerate a revision.
  python manage.py migrate current              Show current revision.
  python manage.py migrate history              Show migration history.

Requirements:
  - Docker daemon running
  - .env file with POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_DB
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent
MIGRATOR_DIR = ROOT / "migrator"

INFRA_SERVICES = ["postgres", "redis", "prometheus", "node_exporter", "postgres_exporter", "redis_exporter"]
BOT_SERVICES = ["bot"]
ALL_SERVICES = [*INFRA_SERVICES, *BOT_SERVICES]

RESET = "\033[0m"
CYAN = "\033[1;36m"
GREEN = "\033[32m"
RED = "\033[31m"

COMMANDS: dict[str, str] = {
    "start": "Start services (infra / bot / all)",
    "stop": "Stop services (infra / bot / all)",
    "down": "Tear down all services, keep volumes",
    "remove": "Tear down all services and delete volumes",
    "migrate": "Run Alembic migrations",
}

MIGRATE_SUBCOMMANDS: dict[str, str] = {
    "upgrade": "Apply pending migrations",
    "generate": "Autogenerate a revision",
    "current": "Show current revision",
    "history": "Show migration history",
}


class Manager:
    """Management commands for the SFA Bot project."""

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def info(msg: str) -> None:
        print(f"{CYAN}>{RESET} {msg}")

    @staticmethod
    def ok(msg: str) -> None:
        print(f"  {GREEN}OK{RESET} {msg}")

    @staticmethod
    def fail(msg: str) -> NoReturn:
        print(f"  {RED}ERR{RESET} {msg}")
        sys.exit(1)

    @staticmethod
    def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
        """Run a shell command, streaming output.  Exits on failure."""
        Manager.info(" ".join(cmd))

        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env or os.environ,
            capture_output=False,
        )

        if proc.returncode != 0:
            Manager.fail(f"Command exited with code {proc.returncode}")

    @staticmethod
    def compose(*args: str) -> None:
        """Run ``docker compose`` from the project root."""
        Manager.run(["docker", "compose", *args])

    @staticmethod
    def load_env() -> dict[str, str]:
        """Read ``.env`` into a dict (no interpolation)."""
        result: dict[str, str] = {}
        env_file = ROOT / ".env"

        if not env_file.exists():
            return result

        for line in env_file.read_text().splitlines():
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")
            result[key] = value.strip().strip('"').strip("'")

        return result

    @staticmethod
    def migration_url() -> str:
        """Build the sync database URL for alembic.

        Uses ``MIGRATION_DATABASE_URL`` when set; otherwise composes a
        ``postgresql://`` URL from ``POSTGRES_*`` env vars (pointing at
        localhost since manage.py runs on the host, not in Docker).
        """
        env = Manager.load_env()

        url = env.get("MIGRATION_DATABASE_URL", "")
        if url:
            return url

        user = env.get("POSTGRES_USER", "sfa")
        password = env.get("POSTGRES_PASSWORD", "")
        port = env.get("POSTGRES_PORT", "5432")
        db = env.get("POSTGRES_DB", "sfa")

        return f"postgresql://{user}:{password}@localhost:{port}/{db}"

    @staticmethod
    def resolve_target(target: str | None) -> list[str]:
        """Map ``infra`` / ``bot`` / ``None`` to a list of service names."""
        if target is None:
            return ALL_SERVICES
        if target == "infra":
            return INFRA_SERVICES
        if target == "bot":
            return BOT_SERVICES
        Manager.fail(f"Unknown target: {target}.  Use 'infra' or 'bot'.")

    # -- commands --------------------------------------------------------------

    def start(self, target: str | None = None) -> None:
        """Start services (all when no target given)."""
        services = self.resolve_target(target)
        label = target or "all"
        self.compose("up", "--build", "-d", *services)
        self.ok(f"Started ({label})")

    def stop(self, target: str | None = None) -> None:
        """Stop services (all when no target given)."""
        services = self.resolve_target(target)
        label = target or "all"
        self.compose("stop", *services)
        self.ok(f"Stopped ({label})")

    def down(self) -> None:
        """Tear down all services, keep named volumes."""
        self.compose("down")
        self.ok("Services torn down (volumes kept)")

    def remove(self) -> None:
        """Tear down all services and delete named volumes."""
        self.compose("down", "-v")
        self.ok("Services and volumes removed")

    def migrate(self, args: list[str]) -> None:
        """Run an Alembic command against the project database."""
        if not args or args[0] not in MIGRATE_SUBCOMMANDS:
            print("Available migrate sub-commands:")

            for name, desc in MIGRATE_SUBCOMMANDS.items():
                print(f"  {name:<12}  {desc}")

            sys.exit(1)

        base = ["alembic", "-c", str(MIGRATOR_DIR / "alembic.ini")]

        env = os.environ.copy()
        env["DATABASE_URL"] = self.migration_url()

        subcmd = args[0]

        if subcmd == "upgrade":
            self.run([*base, "upgrade", "head"], env=env)

        elif subcmd == "current":
            self.run([*base, "current"], env=env)

        elif subcmd == "history":
            self.run([*base, "history"], env=env)

        elif subcmd == "generate":
            if len(args) < 2:
                self.fail("migrate generate requires a message")

            self.run([*base, "revision", "--autogenerate", "-m", args[1]], env=env)

        self.ok("Migration command complete")


# -- cli -----------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("Available commands:")

        for name, desc in COMMANDS.items():
            print(f"  {name:<10}  {desc}")

        sys.exit(0)

    cmd_name = sys.argv[1]

    if cmd_name not in COMMANDS:
        print(f"Unknown command: {cmd_name}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)

    manager = Manager()
    handler = getattr(manager, cmd_name)

    if cmd_name in ("start", "stop"):
        target = sys.argv[2] if len(sys.argv) > 2 else None
        if target not in (None, "infra", "bot"):
            print(f"Unknown target: {target}.  Use 'infra' or 'bot'.")
            sys.exit(1)
        handler(target)
    elif cmd_name == "migrate":
        handler(sys.argv[2:])
    else:
        handler()


if __name__ == "__main__":
    main()
