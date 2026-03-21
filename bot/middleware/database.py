from sqlalchemy import create_engine, Column, Integer, BigInteger, String
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    key = Column(String, nullable=False)

    def __repr__(self):
        return f"<User {self.telegram_id} {self.key}>"

# Для SQLite
DATABASE_URL = "sqlite:///private/users.db"


engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)

# Создаем таблицы
def init_db():
    Base.metadata.create_all(engine)
