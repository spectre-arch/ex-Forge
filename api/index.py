import os
import sys

# Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from server import app


class VercelPathMiddleware:
    """Restores the original requested path from Vercel edge headers."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get("HTTP_X_MATCHED_PATH")
        if matched:
            environ["PATH_INFO"] = matched
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

if __name__ == "__main__":
    app.run()
