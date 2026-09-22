from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)   # sih | devpost | campus | unstop | hackerearth | government
    problem_statement = Column(Text)
    category = Column(String)
    url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
