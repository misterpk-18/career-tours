from asgiref.wsgi import WsgiToAsgi
from flask import Flask
from mangum import Mangum
from sqlalchemy import text

from api.auth.routes import auth_bp
from api.jobs.routes import jobs_bp
from api.recommendations.routes import recommendations_bp
from api.resumes.routes import resume_bp
from api.students.routes import students_bp
from api.projects.routes import projects_bp


from config.database import DATABASE_URL, db

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Neon autosuspends idle compute and drops the TCP connection with it, and on
# Lambda the sandbox is frozen between invocations — so a pooled connection is
# very often dead by the time it is reused. pool_pre_ping catches that;
# pool_recycle retires connections first so the ping rarely has to fire.
#
# pool_size is 1 because a Lambda sandbox serves exactly one request at a time;
# max_overflow is headroom, not concurrency. A warm pool beats NullPool here:
# Neon is in ap-southeast-1 while this runs in ap-south-1, so re-handshaking TLS
# on every request would add ~150-200ms of pure latency.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 1,
    "max_overflow": 2,
    "pool_timeout": 10,
    "connect_args": {
        "connect_timeout": 5,
        "application_name": "career-tours-lambda",
    },
}

db.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(students_bp, url_prefix="/api/students")
app.register_blueprint(resume_bp, url_prefix="/api/resumes")
app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")
app.register_blueprint(projects_bp, url_prefix="/api/projects")
app.register_blueprint(jobs_bp, url_prefix="/api/jobs")


@app.route("/")
def health():
    return {"status": "ok"}


@app.route("/db-test")
def db_test():
    result = db.session.execute(text("SELECT current_database()"))

    return {"database": result.scalar()}


# Lambda entrypoint. Mangum speaks ASGI and Flask is a WSGI app, so WsgiToAsgi
# adapts between them — `app` itself, and every blueprint on it, is unchanged.
# api_gateway_base_path is left at its default "/": the blueprint url_prefixes
# already carry the /api segment, so no path stripping is wanted.
_http = Mangum(WsgiToAsgi(app), lifespan="off")


def handler(event, context):
    """One image, two entry points.

    HTTP requests go to Mangum. Background jobs arrive because the function
    invoked *itself* with InvocationType='Event' and a `ct_task` key — a shape
    that matches none of Mangum's four infer() predicates. Mangum raises rather
    than ignoring an event it cannot classify ("unable to infer a handler"), so
    the task branch has to come first.

    The app context pushed here is what lets the worker use every existing
    repository unchanged; they all reach for `db.session`.
    """
    if isinstance(event, dict) and "ct_task" in event:
        from services.jobs.worker import run_task

        with app.app_context():
            return run_task(event, context)

    return _http(event, context)


if __name__ == "__main__":
    app.run(debug=True)
