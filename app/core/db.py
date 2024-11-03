from contextlib import contextmanager
from typing import Generator

import sqlmodel
from sqlalchemy import create_engine, Engine
from sqlmodel import Session


def get_engine() -> Engine:
    return create_engine("sqlite:///backend.db", echo=True)


def get_db() -> Generator[Session, None, None]:
    """
    Retrieves new SQLAlchemy Session from connection pool
    :yield: SQLAlchemy Session
    """
    with sqlmodel.Session(get_engine()) as session:
        yield session


@contextmanager
def get_database_session() -> Generator[Session, None, None]:
    with sqlmodel.Session(get_engine()) as session:
        yield session
