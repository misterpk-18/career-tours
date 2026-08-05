from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

# Postgres is hosted on Neon, which only accepts TLS connections, so sslmode is
# always part of the URL. Defaulting it here rather than relying on DB_SSLMODE
# being present keeps a partial .env from silently attempting a plaintext connect.
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

DATABASE_URL = (
    f"postgresql://{quote_plus(os.getenv('DB_USER', ''))}:"
    f"{quote_plus(os.getenv('DB_PASSWORD', ''))}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
    f"?sslmode={DB_SSLMODE}"
)

# JWT / auth configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

db = SQLAlchemy()

# Neon autosuspends idle compute and drops the TCP connection with it, which a
# local Postgres never did. pool_pre_ping catches an already-dead connection;
# pool_recycle retires them first so the ping rarely has to.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
