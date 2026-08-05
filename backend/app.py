from asgiref.wsgi import WsgiToAsgi
from flask import Flask
from mangum import Mangum
from sqlalchemy import text

from api.auth.routes import auth_bp
from api.recommendations.routes import recommendations_bp
from api.resumes.routes import resume_bp
from api.students.routes import students_bp
from api.projects.routes import projects_bp


from config.database import DATABASE_URL, db

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(students_bp, url_prefix="/api/students")
app.register_blueprint(resume_bp, url_prefix="/api/resumes")
app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")
app.register_blueprint(projects_bp, url_prefix="/api/projects")


@app.route("/")
def health():
    return {"status": "ok"}


@app.route("/db-test")
def db_test():
    result = db.session.execute(text("SELECT current_database()"))

    return {"database": result.scalar()}


# Lambda entrypoint. Mangum speaks ASGI and Flask is a WSGI app, so WsgiToAsgi
# adapts between them — `app` itself, and every blueprint on it, is unchanged.
# api_gateway_base_path stays None: the blueprint url_prefixes already carry the
# /api segment, so no path stripping is wanted.
handler = Mangum(WsgiToAsgi(app), lifespan="off")


if __name__ == "__main__":
    app.run(debug=True)
