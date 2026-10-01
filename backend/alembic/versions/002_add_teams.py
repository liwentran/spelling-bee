"""add teams

Revision ID: 002
Revises: 001
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('teams',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.add_column('players', sa.Column('team_id', sa.String(), nullable=True))
    op.create_foreign_key('players_team_id_fkey', 'players', 'teams', ['team_id'], ['id'], ondelete='SET NULL')

    op.add_column('words', sa.Column('team_id', sa.String(), nullable=True))
    op.create_foreign_key('words_team_id_fkey', 'words', 'teams', ['team_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('words_team_id_fkey', 'words', type_='foreignkey')
    op.drop_column('words', 'team_id')
    op.drop_constraint('players_team_id_fkey', 'players', type_='foreignkey')
    op.drop_column('players', 'team_id')
    op.drop_table('teams')
