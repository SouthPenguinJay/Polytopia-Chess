"""The WSGI app to be served."""
from flask import Flask


app = Flask(__name__)


@app.route('/')
def hello_world() -> str:
    """Send a test response."""
    return 'Hello, World!'
