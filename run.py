from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development server only. On AWS we use gunicorn instead.
    app.run(debug=True)
