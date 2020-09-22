"""The WSGI app to be served."""
from endpoints.helpers import app


app.run(debug=True)
