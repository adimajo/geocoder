"""
create app object
"""
import os
from urllib.parse import urlsplit

from flask import Flask, jsonify, redirect, request, url_for
from flask_restx import Api
from werkzeug.exceptions import NotFound

from geocoder import __version__
from geocoder.api.rest import api_rest
from geocoder.geocoding.datapaths import here

DEFAULT_MAX_ROWS = 10_000
DEFAULT_MAX_CONTENT_LENGTH = 10 * 1024 * 1024

# Map tiles of the demo page. Any {z}/{x}/{y} raster tile server works, e.g. a self-hosted one; mind the usage
# policy of public servers (the OpenStreetMap one is meant for light use only).
DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def content_security_policy(tile_url):
    """CSP of the HTML pages: everything is served locally, except the map tiles"""
    host = urlsplit(tile_url.replace("{s}", "x")).netloc.replace("x.", "*.", 1) if "{s}" in tile_url \
        else urlsplit(tile_url).netloc
    scheme = urlsplit(tile_url).scheme or "https"
    return (
        "default-src 'self'; "
        f"img-src 'self' data: {scheme}://{host}; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )


def create_app():
    """
    Creates the model serving Flask app

    :return: Flask app
    """
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(here), "site/templates"),
                static_folder=os.path.join(os.path.dirname(here), "site/static"))
    app.json.sort_keys = False
    app.config['GEOCODER_TILE_URL'] = os.environ.get("GEOCODER_TILE_URL", DEFAULT_TILE_URL)
    csp = content_security_policy(app.config['GEOCODER_TILE_URL'])
    app.config['GEOCODER_MAX_ROWS'] = int(os.environ.get("GEOCODER_MAX_ROWS", DEFAULT_MAX_ROWS))
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("GEOCODER_MAX_CONTENT_LENGTH", DEFAULT_MAX_CONTENT_LENGTH))

    @app.errorhandler(404)
    def handle_404(error):
        # browsers get redirected to the usage page, API clients get a proper 404
        if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
            return redirect(url_for('_use'))
        return jsonify(errors=["Not found"]), 404

    @app.route('/')
    def homepage():
        return redirect(url_for('_home'))

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if response.mimetype == "text/html":
            response.headers.setdefault("Content-Security-Policy", csp)
        return response

    api = Api(
        app=app,
        title='Geocoder',
        version=__version__,
        description='Geocoder pour la France',
        doc="/doc",
        default='mapi',
        default_label='Super API'
    )
    api.add_namespace(api_rest)
    api.error_handlers[NotFound] = lambda error: handle_404(error)
    return app


app = create_app()
