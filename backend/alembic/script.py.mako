"""Alembic migration template."""
revision: str = "${up_revision}"
down_revision: str | None = "${down_revision}"
branch_labels: str | None = ${repr(branch_labels)}
depends_on: str | None = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade to this revision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade from this revision."""
    ${downgrades if downgrades else "pass"}
