import json
import os
import traceback
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.escape
import firebase_admin

from firebase_admin import credentials
from firebase_admin import db
from firebase_admin.db import Reference
from functools import wraps, lru_cache
from typing import Callable, Optional, Any, Dict, List
from dotenv import load_dotenv
from tornado.escape import native_str, parse_qs_bytes
from tornado.options import define, options
from pathlib import Path


define("port", default=8080, help="runs on the given port", type=int)

"""
def protected(f: Callable[..., None]) -> Optional[Callable[..., None]]:
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = tornado.escape.json_decode(args[0].request.body)
        decoded_token = jwt.decode(token['token'], os.environ['jwt_secret'])
        if decoded_token['valid']:
            return f(*args, **kwargs)
        else:
            raise MyAppException(reason="Invalid Token", status_code=401)

    return wrapper


def Authenticated(f: Callable[..., None]) -> Callable[..., None]:
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = tornado.escape.json_decode(args[0].request.body)
        decoded_token = jwt.decode(token['token'], os.environ['jwt_secret'])
        if decoded_token['user'] in args[0].settings['logged_in']:
            return f(*args, **kwargs)
        else:
            raise MyAppException(reason='User is not logged in.', status_code=301)
    return wrapper
"""


class MyAppException(tornado.web.HTTPError):
    pass


class BaseHandler(tornado.web.RequestHandler):
    @staticmethod
    @lru_cache(maxsize=None)
    def db(collection: str) -> Reference:
        return db.reference(collection)

    def prepare(self) -> None:
        self.set_header('Content-Type', 'application/json')

    def extract_data(self, data: Dict[str, List[bytes]], attributes: List[str]) -> None:
        for index, value in enumerate(map(lambda x: x[0].decode("utf-8"), [data[attr] for attr in attributes])):
            setattr(self, attributes[index], value)

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        self.set_header('Content-Type', 'application/json')
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            lines = []
            for line in traceback.format_exception(*kwargs["exc_info"]):
                lines.append(line)
            self.write(json.dumps({
                        'status_code': status_code,
                        'message': self._reason,
                        'traceback': lines,
                }))
        else:
            self.write(json.dumps({
                    'status_code': status_code,
                    'message': self._reason,
                }))


class my404handler(BaseHandler):
    async def get(self) -> None:
        self.write(json.dumps({
                'status_code': 404,
                'message': 'Illegal call'
                }))


class PingHandler(BaseHandler):
    async def get(self) -> None:
        self.write(json.dumps({
                'status_code': 200,
                'message': 'Looks good'
            }))


class AuthHandler(BaseHandler):
    async def post(self) -> None:
        data = parse_qs_bytes(native_str(self.request.body), keep_blank_values=True)
        self.extract_data(data, ["name", "uid", "broadcaster"])

        users = self.db("users") # Get collection

        users.child(self.uid).set({
                "name": self.name,
                "broadcaster": self.broadcaster
            })

        self.write(json.dumps({
                'status_code': 200,
                'message': f'Added {self.name} to Database'
            }))


if __name__ == "__main__":
    load_dotenv()
    options.parse_command_line()

    cred = credentials.Certificate(str(Path(f"./{os.environ['SERVICE_ACCOUNT_FILE']}")))

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ['DB_URL']
    })

    app = tornado.web.Application(
        handlers=[
            (r"/", PingHandler),
            (r"/auth", AuthHandler)
        ],
        default_handler_class = my404handler,
        debug=True,
    )
    http_server = tornado.httpserver.HTTPServer(app)
    print("Listening")
    http_server.listen(int(os.environ.get('PORT', options.port)))
    tornado.ioloop.IOLoop.instance().start()
