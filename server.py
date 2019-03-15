import json
import os
import traceback
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.escape
import jwt

from functools import wraps
from typing import Callable, Optional, Any
from dotenv import load_dotenv
from tornado.escape import native_str, parse_qs_bytes
from motor import motor_tornado as MT
from tornado.options import define, options


define("port", default=8080, help="runs on the given port", type=int)

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


class MyAppException(tornado.web.HTTPError):
    pass

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self) -> MT.MotorDatabase:
        return self.settings['db_client']

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
        extract_data(data, ["name", "uid", "broadcaster"])
        


if __name__ == "__main__":
    load_dotenv()
    options.parse_command_line()
    client = getattr(MT.MotorClient(os.environ['MONGO_URI']), os.environ['DB_NAME'])
    app = tornado.web.Application(
        handlers=[
            (r"/", PingHandler),
            (r"/auth", AuthHandler)
        ],
        default_handler_class = my404handler,
        db_client = client,
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(int(os.environ.get('PORT', options.port)))
    tornado.ioloop.IOLoop.instance().start()