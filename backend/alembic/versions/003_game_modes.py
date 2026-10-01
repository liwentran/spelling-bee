"""game modes: session game_mode, team elimination, team-owned turns

Revision ID: 003
Revises: 002
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('game_mode', sa.String(), nullable=False, server_default='individual'))

    op.add_column('teams', sa.Column('eliminated', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('teams', sa.Column('elimination_round', sa.Integer(), nullable=True))

    # In team mode a turn belongs to a team; player_id is the optional speller
    op.add_column('turns', sa.Column('team_id', sa.String(), nullable=True))
    op.create_foreign_key('turns_team_id_fkey', 'turns', 'teams', ['team_id'], ['id'], ondelete='CASCADE')
    op.alter_column('turns', 'player_id', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Team-only turns can't satisfy NOT NULL player_id
    op.execute("DELETE FROM turns WHERE player_id IS NULL")
    op.alter_column('turns', 'player_id', existing_type=sa.String(), nullable=False)
    op.drop_constraint('turns_team_id_fkey', 'turns', type_='foreignkey')
    op.drop_column('turns', 'team_id')

    op.drop_column('teams', 'elimination_round')
    op.drop_column('teams', 'eliminated')

    op.drop_column('sessions', 'game_mode')
