import json
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List

import firebase_admin
import tornado.httpserver
import tornado.ioloop
import tornado.web
from dotenv import load_dotenv
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin.db import Reference
from tornado.escape import native_str, parse_qs_bytes
from tornado.options import define, options

define("port", default=8080, help="runs on the given port", type=int)


class MyAppException(tornado.web.HTTPError):
    pass


class BaseHandler(tornado.web.RequestHandler):
    @staticmethod
    def db(collection: str) -> Reference:
        return db.reference(collection)

    def prepare(self) -> None:
        self.set_header('Content-Type', 'application/json')

    def extract_data(self, attributes: List[str]) -> Dict[str, str]:
        form_data: Dict[str, str] = {}
        data: Dict[str, List[bytes]] = parse_qs_bytes(native_str(self.request.body), keep_blank_values=True)
        for index, value in enumerate(map(lambda x: x[0].decode("utf-8"), [data[attr] for attr in attributes])):
            form_data[attributes[index]] = value

        return form_data

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
        data: Dict[str, str] = self.extract_data(["name", "uid", "broadcaster"])  # Get the form data
        users: Reference = self.db("users")  # Get collection

        users.child(data['uid']).set({
                'name': data['name'],
                'broadcaster': data['broadcaster']
            })

        self.write(json.dumps({
                'status_code': 200,
                'message': f'Added {data["name"]} to Database'
            }))


class MessageHandler(BaseHandler):
    async def post(self) -> None:
        data: Dict[str, str] = self.extract_data(["channel", "message", "uid"])  # Get the form data
        channel: Reference = self.db("channel")  # Get collection
        users: Reference = self.db("users")

        users_ref: Dict[str, Dict[str, str]] = users.get()

        channel.child(data['uid']).set({
            'name': users_ref[data['uid']]['name'],
            'broadcaster': users_ref[data['uid']]['broadcaster'],
            'message': data['message']
        })

        self.write(json.dumps({
            'status_code': 200,
            'message': 'Message added'
        }))


if __name__ == "__main__":
    load_dotenv()
    options.parse_command_line()

    cred = credentials.Certificate(str(Path(f"./{os.environ['SERVICE_ACCOUNT_FILE']}").resolve()))

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ['DB_URL']
    })

    app = tornado.web.Application(
        handlers=[
            (r"/", PingHandler),
            (r"/auth", AuthHandler),
            (r"/post", MessageHandler),
        ],
        default_handler_class = my404handler,
        debug=True,
        form_data={},
    )
    http_server = tornado.httpserver.HTTPServer(app)
    print("Listening")
    http_server.listen(int(os.environ.get('PORT', options.port)))
    tornado.ioloop.IOLoop.instance().start()
