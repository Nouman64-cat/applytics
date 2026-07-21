"""enable glassdoor job source

Revision ID: 1613d585eeb3
Revises: 32a427339816
Create Date: 2026-07-21 17:25:16.015701

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1613d585eeb3'
down_revision: Union[str, None] = '32a427339816'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

job_source_table = sa.table(
    "job_source",
    sa.column("name", sa.String()),
    sa.column("is_enabled", sa.Boolean()),
)


def upgrade() -> None:
    op.execute(job_source_table.update().where(job_source_table.c.name == "glassdoor").values(is_enabled=True))


def downgrade() -> None:
    op.execute(job_source_table.update().where(job_source_table.c.name == "glassdoor").values(is_enabled=False))
