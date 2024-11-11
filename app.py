# app.py
from anonymization_tool import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
