import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft-delete support.

    Adds a ``deleted_at`` column.  Records are considered **active** when
    ``deleted_at IS NULL``.

    IMPORTANT: SQLAlchemy 2.0 does not support automatic query filtering.
    All queries against soft-deletable models **must** include an explicit
    filter::

        stmt = select(MyModel).where(MyModel.deleted_at.is_(None))

    or use the convenience hybrid property::

        stmt = select(MyModel).where(MyModel.is_active == True)
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @hybrid_property
    def is_active(self) -> bool:
        """Return ``True`` when the record has not been soft-deleted."""
        return self.deleted_at is None

    @is_active.inplace.expression
    @classmethod
    def _is_active_expression(cls):
        return cls.deleted_at.is_(None)
