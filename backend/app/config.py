import os


APP_NAME = os.getenv("APP_NAME", "Re-Points")
APP_ENV = os.getenv("APP_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-value")
SESSION_COOKIE = "re_points_session"
SESSION_MAX_AGE = 60 * 60 * 8
AI_ACCEPT_THRESHOLD = float(os.getenv("AI_ACCEPT_THRESHOLD", "0.85"))

