import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

SERVER = 'http://127.0.0.1:5050'


class ServerError(Exception):
    """A request that did not work. The message is ready to show to the user."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        # the HTTP status code, or 0 when the server could not be reached
        self.status = status


def ask_server(path: str, values: dict | None = None):
    # without values urlopen sends a GET; with values it sends them as a POST form
    data = None
    if values is not None:
        data = urlencode(values).encode('utf-8')
    try:
        with urlopen(SERVER + path, data=data, timeout=5) as reply:
            return json.loads(reply.read().decode('utf-8'))
    # HTTPError is a kind of URLError, so it must come first
    except HTTPError as error:
        # Flask's error replies are JSON such as {"error": "The name must not be empty."}
        try:
            body = error.read().decode('utf-8')
            message = json.loads(body)['error']
        except (ValueError, KeyError):
            message = 'The server answered with error ' + str(error.code) + '.'
        raise ServerError(message, error.code)
    except URLError as error:
        if isinstance(error.reason, socket.timeout):
            raise ServerError('The server took too long to answer. Try again.')
        raise ServerError('Cannot reach the server. Start server.py and try again.')
    except socket.timeout:
        raise ServerError('The server took too long to answer. Try again.')
    except OSError:
        # for example the server stopped in the middle of a reply
        raise ServerError('Cannot reach the server. Start server.py and try again.')
