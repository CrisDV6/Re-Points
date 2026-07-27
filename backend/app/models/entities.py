import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


def current_time() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    CLIENT = "client"
    ESTABLISHMENT_ADMIN = "establishment_admin"
    SUPERADMIN = "superadmin"


class WasteType(str, enum.Enum):
    PLASTIC = "plastic"
    GLASS = "glass"
    UNKNOWN = "unknown"


class MovementType(str, enum.Enum):
    EARNED = "earned"
    REDEEMED = "redeemed"
    ADJUSTMENT = "adjustment"


class RedemptionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    public_identifier: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    admin_assignments: Mapped[list["EstablishmentAdmin"]] = relationship(back_populates="user")
    balances: Mapped[list["CustomerBalance"]] = relationship(back_populates="user")
    recycling_events: Mapped[list["RecyclingEvent"]] = relationship(back_populates="user")
    point_movements: Mapped[list["PointMovement"]] = relationship(back_populates="user")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="user")
    qr_validation_attempts: Mapped[list["QrValidationAttempt"]] = relationship(
        foreign_keys="QrValidationAttempt.operator_id",
        back_populates="operator",
    )


class Establishment(Base):
    __tablename__ = "establishments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plastic_points: Mapped[int] = mapped_column(Integer, default=5)
    glass_points: Mapped[int] = mapped_column(Integer, default=8)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time, onupdate=current_time)

    administrators: Mapped[list["EstablishmentAdmin"]] = relationship(back_populates="establishment")
    balances: Mapped[list["CustomerBalance"]] = relationship(back_populates="establishment")
    recycling_events: Mapped[list["RecyclingEvent"]] = relationship(back_populates="establishment")
    point_movements: Mapped[list["PointMovement"]] = relationship(back_populates="establishment")
    rewards: Mapped[list["Reward"]] = relationship(back_populates="establishment")
    settings: Mapped[list["Setting"]] = relationship(back_populates="establishment")
    devices: Mapped[list["Device"]] = relationship(back_populates="establishment")
    reward_rules: Mapped[list["LocalRewardRule"]] = relationship(back_populates="establishment")


class EstablishmentAdmin(Base):
    __tablename__ = "establishment_admins"
    __table_args__ = (UniqueConstraint("user_id", "establishment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    user: Mapped[User] = relationship(back_populates="admin_assignments")
    establishment: Mapped[Establishment] = relationship(back_populates="administrators")


class QrValidationAttempt(Base):
    __tablename__ = "qr_validation_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    matched_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scanned_identifier: Mapped[str] = mapped_column(String(100))
    successful: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    operator: Mapped[User] = relationship(
        foreign_keys=[operator_id],
        back_populates="qr_validation_attempts",
    )
    matched_user: Mapped[User | None] = relationship(foreign_keys=[matched_user_id])


class CustomerBalance(Base):
    __tablename__ = "customer_balances"
    __table_args__ = (UniqueConstraint("user_id", "establishment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    points: Mapped[int] = mapped_column(Integer, default=0)
    total_points_earned: Mapped[int] = mapped_column(Integer, default=0)
    total_points_redeemed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    user: Mapped[User] = relationship(back_populates="balances")
    establishment: Mapped[Establishment] = relationship(back_populates="balances")


class RecyclingEvent(Base):
    __tablename__ = "recycling_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_identifier: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    waste_type: Mapped[WasteType] = mapped_column(Enum(WasteType))
    bottle_count: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="accepted")
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    user: Mapped[User] = relationship(back_populates="recycling_events")
    establishment: Mapped[Establishment] = relationship(back_populates="recycling_events")
    point_movement: Mapped["PointMovement | None"] = relationship(back_populates="recycling_event")
    device: Mapped["Device | None"] = relationship(back_populates="recycling_events")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(120))
    api_key_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_connection: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time, onupdate=current_time)

    establishment: Mapped[Establishment] = relationship(back_populates="devices")
    recycling_events: Mapped[list[RecyclingEvent]] = relationship(back_populates="device")


class LocalRewardRule(Base):
    __tablename__ = "local_reward_rules"
    __table_args__ = (UniqueConstraint("establishment_id", "material"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    material: Mapped[WasteType] = mapped_column(Enum(WasteType))
    points: Mapped[int] = mapped_column(Integer)
    minimum_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.80"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time, onupdate=current_time)

    establishment: Mapped[Establishment] = relationship(back_populates="reward_rules")


class PointMovement(Base):
    __tablename__ = "point_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    recycling_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("recycling_events.id"), unique=True, nullable=True
    )
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType))
    points: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    user: Mapped[User] = relationship(back_populates="point_movements")
    establishment: Mapped[Establishment] = relationship(back_populates="point_movements")
    recycling_event: Mapped[RecyclingEvent | None] = relationship(back_populates="point_movement")


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    points_required: Mapped[int] = mapped_column(Integer)
    available_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    establishment: Mapped[Establishment] = relationship(back_populates="rewards")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="reward")


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"))
    points_spent: Mapped[int] = mapped_column(Integer)
    status: Mapped[RedemptionStatus] = mapped_column(
        Enum(RedemptionStatus), default=RedemptionStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_time)

    user: Mapped[User] = relationship(back_populates="redemptions")
    reward: Mapped[Reward] = relationship(back_populates="redemptions")


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("establishment_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    establishment_id: Mapped[int | None] = mapped_column(
        ForeignKey("establishments.id"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    establishment: Mapped[Establishment | None] = relationship(back_populates="settings")
