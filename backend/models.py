from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    name_en = Column(String)
    color = Column(String, default="#6366f1")
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    keywords = relationship("Keyword", back_populates="domain", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    name = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    domain = relationship("Domain", back_populates="keywords")
    papers = relationship("Paper", back_populates="keyword", cascade="all, delete-orphan")
    patents = relationship("Patent", back_populates="keyword", cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    paper_id = Column(String, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    year = Column(Integer)
    citation_count = Column(Integer, default=0)
    authors = Column(Text)
    url = Column(String)
    doi = Column(String)
    collected_at = Column(DateTime, server_default=func.now())

    keyword = relationship("Keyword", back_populates="papers")


class Patent(Base):
    __tablename__ = "patents"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    patent_id = Column(String, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    year = Column(Integer)
    assignee = Column(String)
    inventors = Column(Text)
    country = Column(String)
    url = Column(String)
    collected_at = Column(DateTime, server_default=func.now())

    keyword = relationship("Keyword", back_populates="patents")
