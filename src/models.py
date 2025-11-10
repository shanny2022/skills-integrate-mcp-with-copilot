from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    activity_id: int = Field(foreign_key="activity.id")

    # Relationships
    user: "User" = Relationship(back_populates="participants")
    activity: "Activity" = Relationship(back_populates="participants")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)

    participants: List[Participant] = Relationship(back_populates="user")


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    schedule: Optional[str] = None
    max_participants: Optional[int] = None

    participants: List[Participant] = Relationship(back_populates="activity")
