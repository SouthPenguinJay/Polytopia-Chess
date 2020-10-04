"""Run the server."""
from .endpoints.helpers import app
from .events.helpers import socketio


socketio.run(app)
