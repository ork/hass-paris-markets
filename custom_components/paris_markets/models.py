"""Data models for the Paris Markets integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util


class ProductType(Enum):
    """Enum for market product types."""

    ALIMENTAIRE = "Alimentaire"
    ALIMENTAIRE_BIO = "Alimentaire bio"
    FLEURS = "Fleurs"
    OISEAUX = "Oiseaux"
    TIMBRES = "Timbres"
    PUCES = "Puces"
    BROCANTE = "Brocante"
    CREATION_ARTISTIQUE = "Création artistique"


class FilterMode(Enum):
    """Enum for filter modes."""

    RADIUS = "radius"
    ARRONDISSEMENT = "arrondissement"


class Arrondissement(Enum):
    """Enum for Paris arrondissements."""

    FIRST = 1
    SECOND = 2
    THIRD = 3
    FOURTH = 4
    FIFTH = 5
    SIXTH = 6
    SEVENTH = 7
    EIGHTH = 8
    NINTH = 9
    TENTH = 10
    ELEVENTH = 11
    TWELFTH = 12
    THIRTEENTH = 13
    FOURTEENTH = 14
    FIFTEENTH = 15
    SIXTEENTH = 16
    SEVENTEENTH = 17
    EIGHTEENTH = 18
    NINETEENTH = 19
    TWENTIETH = 20


class WeekDay(Enum):
    """Enum for days of the week."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    @classmethod
    def from_date(cls, date: date) -> "WeekDay":
        """Get the ISO weekday enum from a date."""
        return cls(date.isoweekday())


@dataclass
class MarketDaySchedule:
    """Data class for market day schedule."""

    start_time: time | None
    end_time: time | None

    def __post_init__(self):
        """Post-initialisation to ensure times are timezone-aware."""
        if self.start_time is not None and self.end_time is not None:
            if self.start_time.tzinfo is None:
                raise ValueError("Start time must be timezone-aware.")
            if self.end_time.tzinfo is None:
                raise ValueError("End time must be timezone-aware.")
        if self.start_time is None and self.end_time is not None:
            raise ValueError("If end time is set, start time must also be set.")
        if self.start_time is not None and self.end_time is None:
            raise ValueError("If start time is set, end time must also be set.")

    def is_open(self) -> bool:
        """Check if the market is open."""
        return self.start_time is not None and self.end_time is not None

    @classmethod
    def from_maybe_dict(cls, data: dict[str, time] | None) -> "MarketDaySchedule":
        """Create MarketDaySchedule from a dictionary."""
        if data is None:
            return cls(start_time=None, end_time=None)

        return cls(start_time=data.get("start_time"), end_time=data.get("end_time"))

    def as_local_datetimes(self, date: date) -> tuple[datetime, datetime] | None:
        """Return start and end times as local datetimes."""
        if not self.is_open():
            return None

        return (
            dt_util.as_local(datetime.combine(date, self.start_time)),  # type: ignore[arg-type]
            dt_util.as_local(datetime.combine(date, self.end_time)),  # type: ignore[arg-type]
        )


@dataclass
class MarketData:
    """Data class for market information."""

    market_id: str
    long_name: str
    short_name: str
    arrondissement: int
    location: str
    product_type: str
    coordinates: dict
    schedule: dict[WeekDay, MarketDaySchedule]

    @classmethod
    def from_coordinator(
        cls, coordinator: type[DataUpdateCoordinator], market_id: str
    ) -> Optional["MarketData"]:
        """Create MarketData from coordinator data."""
        if coordinator.data is None:
            return None

        data = coordinator.data.get(market_id)
        if not data:
            return None

        schedule = {
            WeekDay(day_id): MarketDaySchedule.from_maybe_dict(day_schedule)
            for day_id, day_schedule in data["schedule"].items()
        }

        return cls(
            market_id=data["market_id"],
            long_name=data["long_name"],
            short_name=data["short_name"],
            arrondissement=int(data["arrondissement"]),
            location=data["location"],
            product_type=data["product_type"],
            coordinates=data["coordinates"],
            schedule=schedule,
        )
