from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from sqlalchemy.ext.declarative import declarative_base


load_dotenv()

engine = create_engine(os.getenv("DB_DSN"))
Base = declarative_base()

from sqlalchemy import Column, Integer, String, Enum

import enum


class FaithStatus(enum.Enum):
    unknown = 1
    seeker = 2
    believer = 3
    baptized = 4


class Role(enum.Enum):
    none = 1
    facilitator = 2
    counselor = 3


class Active(enum.Enum):
    false = 0
    true = 1


class Lamb(Base):
    __tablename__ = "lambs"
    id = Column(Integer, primary_key=True)
    given_name = Column(String)
    surname = Column(String)
    faith_status = Column(Enum(FaithStatus))
    role = Column(Enum(Role))
    active = Column(Enum(Active))
    notes = Column(String)
