from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_url = "sqlite:///./FoodFrezn.db"
engine = create_engine(db_url, connect_args={"check_same_thread":False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
