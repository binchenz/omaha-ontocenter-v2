from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class DataSourceType(str, enum.Enum):
    csv = "csv"
    excel = "excel"
    mysql = "mysql"
    postgres = "postgres"
    sqlite = "sqlite"


class DataSourceStatus(str, enum.Enum):
    active = "active"
    error = "error"
    disconnected = "disconnected"


class DataSource(Base):
    __tablename__ = "datasources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[DataSourceType] = mapped_column(SQLEnum(DataSourceType), nullable=False)
    config: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted JSON
    status: Mapped[DataSourceStatus] = mapped_column(
        SQLEnum(DataSourceStatus), default=DataSourceStatus.active
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="datasource")


class DatasetStatus(str, enum.Enum):
    syncing = "syncing"
    ready = "ready"
    error = "error"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    datasource_id: Mapped[str] = mapped_column(String, ForeignKey("datasources.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    rows_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_schedule: Mapped[str] = mapped_column(String, default="manual")
    status: Mapped[DatasetStatus] = mapped_column(SQLEnum(DatasetStatus), default=DatasetStatus.ready)
    delta_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    datasource: Mapped["DataSource"] = relationship(back_populates="datasets")
