import json
import os
import traceback
import tornado.httpserver
import tornado.ioloop
import tornado.web
from motor import motor_tornado
from tornado.options import define, options
import tornado.escape
import jwt
from functools import wraps

define("port", default=8080, help="runs on the given port", type=int)


class MyAppException(tornado.web.HTTPError):
    pass


def protected(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = tornado.escape.json_decode(args[0].request.body)
        decoded_token = jwt.decode(token['token'], os.environ['jwt_secret'])
        if decoded_token['valid']:
            return f(*args, **kwargs)
        else:
            raise MyAppException(reason="Invalid Token", status_code=401)
    return wrapper


def Authenticated(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = tornado.escape.json_decode(args[0].request.body)
        decoded_token = jwt.decode(token['token'], os.environ['jwt_secret'])
        if decoded_token['user'] in args[0].settings['logged_in']:
            return f(*args, **kwargs)
        else:
            raise MyAppException(reason='User is not logged in.', status_code=301)
    return wrapper


class BaseHandler(tornado.web.RequestHandler):
    def db(self):
        clientz = self.settings['db_client']
        db = clientz.tornado
        return db

    def write_error(self, status_code, **kwargs):
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
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
                'status_code': 404,
                'message': 'illegal call.'
        }))




if __name__ == "__main__":
    options.parse_command_line()
    app = tornado.web.Application(
        handlers=[
        ],
        default_handler_class = my404handler,
        db_client = client,
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(os.environ.get("PORT", options.port))
    tornado.ioloop.IOLoop.instance().start()