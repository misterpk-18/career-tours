from flask import Flask
from sqlalchemy import text

from api.recommendations.routes import recommendations_bp
from api.resumes.routes import resume_bp
from api.students.routes import students_bp
from api.projects.routes import projects_bp
from api.recommendations.routes import recommendations_bp


from config.database import DATABASE_URL, db

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

app.register_blueprint(students_bp, url_prefix="/api/students")
app.register_blueprint(resume_bp, url_prefix="/api/resumes")
app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")
app.register_blueprint(projects_bp, url_prefix="/api/projects")
app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")

@app.route("/")
def health():
    return {"status": "ok"}


@app.route("/db-test")
def db_test():
    result = db.session.execute(
        text("SELECT current_database()")
    )

    return {
        "database": result.scalar()
    }
if __name__ == "__main__":
    app.run(debug=True)
