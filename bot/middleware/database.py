from sqlalchemy import create_engine, Column, Integer, BigInteger, String, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

MAX_SUBSCRIPTIONS = 5

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    key = Column(String, nullable=False)  # group number or teacher FIO
    type = Column(String, nullable=False)  # "group" or "teacher"

    __table_args__ = (
        UniqueConstraint('telegram_id', 'key', name='uq_user_key'),
    )

    def __repr__(self):
        return f"<Subscription {self.telegram_id} {self.type}:{self.key}>"


# Обратная совместимость — алиас
User = Subscription

# Для SQLite
from pathlib import Path as _Path
_db_dir = _Path(__file__).resolve().parent.parent.parent / "data"
_db_dir.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{_db_dir / 'users.db'}"

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)
