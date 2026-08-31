"""retire the seeded appraise-only account

Revision ID: 009_retire_officer
Revises: 008_drop_cost_realism

`008` removed `users.can_sanction`, and with it `require_sanction`. That is correct for
the two roles the product now has, but it silently PROMOTED the one account the flag was
holding back: `officer@demo.gov.in` is a `ministry` row, so once the gate was gone it
could sanction. Dropping a permission column has to account for whoever the column was
denying, or the removal hands them the permission instead of taking it away.

Deactivated rather than deleted, deliberately. `audit_events.actor_id` has carried no
foreign key since `005`, so a DELETE would leave the events behind with an id that
resolves to nothing — `governance.py` looks the actor up to name them, and every decision
that account recorded would lose its author. Invariant: the trail must outlive the row it
describes (`004`). `is_active = false` refuses the login in both `/auth/login` and
`current_user`, which is the whole of what "remove the officer login" needs, while the
name stays resolvable.

Idempotent: `start.sh` runs `alembic upgrade head` on every boot, and the UPDATE matches
nothing on a database that never seeded the account.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_retire_officer"
down_revision: str | None = "008_drop_cost_realism"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RETIRED = "officer@demo.gov.in"


def upgrade() -> None:
    op.execute(sa.text("UPDATE users SET is_active = false WHERE email = :e")
               .bindparams(e=RETIRED))


def downgrade() -> None:
    # Reactivating restores the login, not the appraise-only limit — that lived in
    # can_sanction, which 008 drops. Downgrade past 008 as well to get the gate back.
    op.execute(sa.text("UPDATE users SET is_active = true WHERE email = :e")
               .bindparams(e=RETIRED))
