import os
import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250), nullable=False)

class Catalog(Base):
    __tablename__ = 'catalog'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)


class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(512), nullable=False)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    catalog_id = Column(Integer, ForeignKey('catalog.id'))
    catalog = relationship(Catalog)


engine = create_engine('sqlite:///itemcatalog.db')


Base.metadata.create_all(engine)
