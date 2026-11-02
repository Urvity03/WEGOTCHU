"""merge trips and SOS migrations

Revision ID: 8255d79f0615
Revises: b11a8c8f4cc6, bdb14f4d4138
Create Date: 2026-10-31 00:14:36.334896

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8255d79f0615"
down_revision: Union[str, Sequence[str], None] = ("b11a8c8f4cc6", "bdb14f4d4138")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
