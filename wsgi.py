#!/usr/bin/env python3
"""
WSGI Entry Point for Protocol Pulse
Compatible with both gunicorn and uvicorn deployments
"""

from app import app as flask_app
import os

# For gunicorn (WSGI)
application = flask_app
app = flask_app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)
