"""seed job sources

Revision ID: a70df6ac8a1a
Revises: 09d928c79fdf
Create Date: 2026-07-21 16:50:18.407345

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a70df6ac8a1a'
down_revision: Union[str, None] = '09d928c79fdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

job_source_table = sa.table(
    "job_source",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("is_enabled", sa.Boolean()),
    sa.column("rate_limit_per_min", sa.Integer()),
    sa.column("auth_config", sa.JSON()),
)

SOURCES = [
    {"name": "adzuna", "is_enabled": True, "rate_limit_per_min": 60},
    {"name": "linkedin", "is_enabled": False, "rate_limit_per_min": None},
    {"name": "indeed", "is_enabled": False, "rate_limit_per_min": None},
    {"name": "glassdoor", "is_enabled": False, "rate_limit_per_min": None},
    {"name": "jobwright", "is_enabled": False, "rate_limit_per_min": None},
]


def upgrade() -> None:
    op.bulk_insert(
        job_source_table,
        [{**source, "id": uuid.uuid4(), "auth_config": {}} for source in SOURCES],
    )


def downgrade() -> None:
    names = [source["name"] for source in SOURCES]
    op.execute(job_source_table.delete().where(job_source_table.c.name.in_(names)))
