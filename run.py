from app import app

if __name__ == '__main__':
    app.run(
        host=app.config.get("APP_HOST", "0.0.0.0"),
        port=app.config.get("APP_PORT", 8000),
        debug=app.config.get("DEBUG", True),
    )
