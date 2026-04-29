from sqlalchemy import create_engine, BigInteger, Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func


Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    key = Column(String, nullable=False)

    def __repr__(self):
        return f"<User {self.telegram_id} {self.key}>"


class ChangeDetails(Base):
    __tablename__ = "change_details"
    id = Column(Integer, primary_key=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    change_type = Column(Enum("added", "removed", "changed", name="ctype"))
    event_id = Column(String(50), nullable=False)
    group_name = Column(String(10), nullable=False)
    weekday = Column(String(2), nullable=False)
    pair_number = Column(Integer, nullable=False)
    time = Column(String(5), nullable=False)

    # Для 'changed'
    field_name = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

# Для SQLite
DATABASE_URL = "sqlite:///private/users.db"


engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)

# Создаем таблицы
def init_db():
    Base.metadata.create_all(engine)
