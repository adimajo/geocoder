"""
defines all routes

.. autosummary::
    get_jsoned_geocoded_data
    geocode_one
    geocode_file
"""
import json

from flask import current_app, jsonify, make_response, render_template, request
from flask_restx import Namespace, Resource

from geocoder import __version__
from geocoder.api.Geocoder import Geocoder
from geocoder.columns import ADDRESS, CITY, POSTAL_CODE

QUALITY = {'1': 'Successful',
           '2': 'Precise number was not found',
           '3': 'Precise number was not found and there was no number in the input',
           '4': 'Street was not found',
           '5': 'City was not found',
           '6': 'Nothing was found'}

api_rest = Namespace('')


@api_rest.route("/home")
class Home(Resource):
    """
    Render homepage

    Methods
    -------
    get:
        get method for Home resource: outputs the homepage

    """
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template("index.html", version=__version__,
                                                tile_url=current_app.config["GEOCODER_TILE_URL"]), 200, headers)


@api_rest.route("/version")
class Version(Resource):
    """
    Flask resource to spit current version

    Methods
    -------
    get:
        get method for Version resource: outputs the current version of the geocoder

    """
    @api_rest.doc(responses={200: 'Version of the geocoder API'})
    @api_rest.doc(responses={500: 'All other server errors'})
    def get(self):
        return jsonify(version=__version__)


@api_rest.route("/use")
class Use(Resource):
    """
    Render Use

    Methods
    -------
    get:
        get method for Use resource: shows how to use the API

    """
    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template("use_rest.html"), 200, headers)


def get_jsoned_geocoded_data(geocoder):
    output_json = {
        'uuid': geocoder.uuid,
        'geocoded_time': geocoder.get_geocoded_date_time().strftime('%Y-%m-%d %H:%M:%S.%f%z')
        if geocoder.geocoded else None,
        'api_version': __version__,
        'quality': QUALITY,
    }
    if geocoder.geocoded:
        output_json['data'] = geocoder.get_geocoded_data()
    else:
        output_json['errors'] = geocoder.get_errors() or 'Data not geocoded !'
    return output_json


def _error(status, message):
    response = jsonify(errors=[message], api_version=__version__)
    response.status_code = status
    return response


def _geocode(records):
    geocoder = Geocoder(records)
    geocoder.geocode()
    response = jsonify(get_jsoned_geocoded_data(geocoder))
    if not geocoder.geocoded:
        response.status_code = 400
    return response


@api_rest.route("/geocode/<address>/<postal_code>/<city>", methods=["GET"])
class GeocodeOne(Resource):
    @api_rest.doc(responses={200: 'Geocoded address', 400: 'Invalid input'})
    def get(self, address, postal_code, city):
        return _geocode([{ADDRESS: address, POSTAL_CODE: postal_code, CITY: city}])


@api_rest.route("/geocode_file", methods=["POST"])
class GeocodeFile(Resource):
    @api_rest.doc(responses={200: 'Geocoded addresses', 400: 'Invalid input', 413: 'Too many rows or body too large'})
    def post(self):
        payload = request.get_json(force=True, silent=True)
        if isinstance(payload, str):  # legacy clients send a JSON document encoded as a JSON string
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = None
        if not isinstance(payload, list):
            return _error(400, "The body must be a JSON list of objects "
                               '[{"address": "...", "postal_code": "...", "city": "..."}].')
        max_rows = current_app.config["GEOCODER_MAX_ROWS"]
        if len(payload) > max_rows:
            return _error(413, f"Too many rows: at most {max_rows} addresses per request.")
        return _geocode(payload)
