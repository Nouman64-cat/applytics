"""enable indeed and jobwright job sources

Revision ID: 49ba099da294
Revises: e43292e1ec05
Create Date: 2026-07-21 20:14:34.203260

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '49ba099da294'
down_revision: Union[str, None] = 'e43292e1ec05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

job_source_table = sa.table(
    "job_source",
    sa.column("name", sa.String()),
    sa.column("is_enabled", sa.Boolean()),
)


def upgrade() -> None:
    op.execute(
        job_source_table.update()
        .where(job_source_table.c.name.in_(["indeed", "jobwright"]))
        .values(is_enabled=True)
    )


def downgrade() -> None:
    op.execute(
        job_source_table.update()
        .where(job_source_table.c.name.in_(["indeed", "jobwright"]))
        .values(is_enabled=False)
    )
