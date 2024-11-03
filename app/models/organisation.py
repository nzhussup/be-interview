from sqlmodel import Field, Relationship
from app.models.base import Base


class CreateOrganisation(Base):
    name: str


class Organisation(Base, table=True):
    id: int | None = Field(primary_key=True)
    name: str