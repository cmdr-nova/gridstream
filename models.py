from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
# This is the models where I keep all the database stuff
class Folder(Base):
    __tablename__ = 'folders'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    feeds = relationship('Feed', back_populates='folder')

class Feed(Base):
    __tablename__ = 'feeds'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    folder_id = Column(Integer, ForeignKey('folders.id'))
    folder = relationship('Folder', back_populates='feeds')

engine = create_engine('sqlite:///rss_reader.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
