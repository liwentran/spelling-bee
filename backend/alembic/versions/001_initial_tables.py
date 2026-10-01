"""initial tables

Revision ID: 001
Revises: 
Create Date: 2026-09-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('timer_duration_seconds', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('elimination_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(), nullable=False, server_default='setup'),
        sa.Column('current_round', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('players',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('age', sa.String(), nullable=True),
        sa.Column('grade', sa.String(), nullable=True),
        sa.Column('school', sa.String(), nullable=True),
        sa.Column('fun_fact', sa.String(), nullable=True),
        sa.Column('eliminated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('elimination_round', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('words',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('player_id', sa.String(), nullable=True),
        sa.Column('word', sa.String(), nullable=False),
        sa.Column('definition', sa.String(), nullable=True),
        sa.Column('sentence', sa.String(), nullable=True),
        sa.Column('part_of_speech', sa.String(), nullable=True),
        sa.Column('language_of_origin', sa.String(), nullable=True),
        sa.Column('alternate_pronunciations', sa.String(), nullable=True),
        sa.Column('difficulty', sa.Integer(), nullable=True),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('turns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('player_id', sa.String(), nullable=False),
        sa.Column('word_id', sa.String(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('result', sa.String(), nullable=False),
        sa.Column('time_taken_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['word_id'], ['words.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('turns')
    op.drop_table('words')
    op.drop_table('players')
    op.drop_table('sessions')
