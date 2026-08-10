from flask_sqlalchemy import SQLAlchemy
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
# local Postgres never did. The pooling that guards against that lives in
# SQLALCHEMY_ENGINE_OPTIONS in app.py, because `db` builds its own engine from
# the Flask config — a create_engine() call here would produce a second engine
# that nothing uses, which is exactly the trap this file previously fell into.
