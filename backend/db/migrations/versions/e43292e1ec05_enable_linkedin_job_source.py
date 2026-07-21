"""enable linkedin job source

Revision ID: e43292e1ec05
Revises: 1613d585eeb3
Create Date: 2026-07-21 19:45:26.751064

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e43292e1ec05'
down_revision: Union[str, None] = '1613d585eeb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

job_source_table = sa.table(
    "job_source",
    sa.column("name", sa.String()),
    sa.column("is_enabled", sa.Boolean()),
)


def upgrade() -> None:
    op.execute(job_source_table.update().where(job_source_table.c.name == "linkedin").values(is_enabled=True))


def downgrade() -> None:
    op.execute(job_source_table.update().where(job_source_table.c.name == "linkedin").values(is_enabled=False))
