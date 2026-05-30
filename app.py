from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS

from config import Config
from services.auth_service import AuthService
from services.groq_service import GroqCareerService, RoadmapServiceError


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, supports_credentials=True)

    auth_service = AuthService(app.config["DATABASE_PATH"])
    career_service = GroqCareerService(
        api_key=app.config["GROQ_API_KEY"],
        model=app.config["GROQ_MODEL"],
        mock_when_no_key=app.config["MOCK_AI_WHEN_NO_KEY"],
    )

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/auth/me")
    def auth_me():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"user": None}), 200
        return jsonify({"user": auth_service.get_user_by_id(user_id)}), 200

    @app.post("/auth/register")
    def auth_register():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        validation_error = _validate_auth_payload(name, email, password)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        user = auth_service.create_user(name=name, email=email, password=password)
        if not user:
            return jsonify({"error": "An account with this email already exists."}), 409

        session["user_id"] = user["id"]
        return jsonify({"user": user, "message": "Account created successfully."}), 201

    @app.post("/auth/login")
    def auth_login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        user = auth_service.authenticate(email=email, password=password)
        if not user:
            return jsonify({"error": "Invalid email or password."}), 401

        session["user_id"] = user["id"]
        return jsonify({"user": user, "message": "Logged in successfully."}), 200

    @app.post("/auth/logout")
    def auth_logout():
        session.clear()
        return jsonify({"message": "Logged out successfully."}), 200

    @app.post("/generate-roadmap")
    def generate_roadmap():
        data = request.get_json(silent=True) or {}
        validation_error = _validate_profile_payload(data)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        try:
            roadmap = career_service.generate_roadmap(data)
            return jsonify(roadmap), 200
        except RoadmapServiceError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            app.logger.exception("Unexpected roadmap generation error")
            return jsonify({"error": "Something went wrong while generating your roadmap."}), 500

    @app.post("/analyze-skills")
    def analyze_skills():
        data = request.get_json(silent=True) or {}
        validation_error = _validate_profile_payload(data)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        try:
            analysis = career_service.analyze_skills(data)
            return jsonify(analysis), 200
        except RoadmapServiceError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            app.logger.exception("Unexpected skill analysis error")
            return jsonify({"error": "Something went wrong while analyzing your skills."}), 500

    @app.post("/chat")
    def chat():
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Message is required."}), 400

        try:
            answer = career_service.chat(
                message=message,
                profile=data.get("profile") or {},
                roadmap_context=data.get("roadmapContext") or {},
            )
            return jsonify(answer), 200
        except RoadmapServiceError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            app.logger.exception("Unexpected mentor chat error")
            return jsonify({"error": "Something went wrong while talking to the AI mentor."}), 500

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Endpoint not found."}), 404

    return app


def _validate_profile_payload(data):
    skills = (data.get("skills") or "").strip()
    level = (data.get("experienceLevel") or "").strip()
    target_role = (data.get("targetRole") or "").strip()

    if not skills:
        return "Current skills are required."
    if level not in {"Beginner", "Intermediate", "Advanced"}:
        return "Experience level must be Beginner, Intermediate, or Advanced."
    if not target_role:
        return "Target role is required."
    return None


def _validate_auth_payload(name, email, password):
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if "@" not in email or "." not in email:
        return "Enter a valid email address."
    if len(password) < 6:
        return "Password must be at least 6 characters."
    return None


app = create_app()


if __name__ == "__main__":
    app.run(debug=Config.FLASK_DEBUG, host="127.0.0.1", port=5000)
