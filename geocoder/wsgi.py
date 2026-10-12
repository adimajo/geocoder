"""
A simple wsgi server
"""
import platform

from geocoder.api.provider import app
from geocoder.geocoding.utils import env_bool

if platform.uname().system.lower() == 'linux':
    import gunicorn.app.base

    class StandaloneApplication(gunicorn.app.base.BaseApplication):

        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            config = {key: value for key, value in self.options.items()
                      if key in self.cfg.settings and value is not None}
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application


def runserver(options):
    """
    Serves the app: gunicorn on Linux, the Flask development server elsewhere

    The Flask debugger (remote code execution when exposed) is only enabled with :code:`FLASK_DEBUG=1`.
    """
    options = dict(options)
    host, port = options.pop('host'), options.pop('port')
    if platform.uname().system.lower() == 'linux':
        # preload so that the memory-mapped database is shared by all workers
        options.update({"bind": f"{host}:{port}", "preload_app": True, "control_socket_disable": True})
        StandaloneApplication(app, options).run()
    else:  # pragma: no cover
        app.run(host=host, port=int(port), debug=env_bool("FLASK_DEBUG", False))


if __name__ == '__main__':  # pragma: no cover
    app.run(host='127.0.0.1', port=8001, debug=env_bool("FLASK_DEBUG", False))
