"""Run the server."""
from .endpoints.helpers import app


app.run(debug=True)
