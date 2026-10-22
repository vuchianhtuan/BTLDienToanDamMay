from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_database(url):
    engine = create_engine(
        url, pool_pre_ping=True,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    return engine, sessionmaker(engine, expire_on_commit=False)
