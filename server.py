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
from firebase_admin.credentials import Certificate
from firebase_admin.db import Reference, Query
from tornado.escape import native_str, parse_qs_bytes
from tornado.httpserver import HTTPServer
from tornado.options import define, options
from tornado.web import Application

define("port", default=8080, help="runs on the given port", type=int)


class MyAppException(tornado.web.HTTPError):
    pass


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self) -> None:
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    @staticmethod
    def db(collection: str) -> object:
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

            reason = kwargs['reason'] if kwargs['reason'] else self._reason
            self.write(json.dumps({
                    'status_code': status_code,
                    'message': reason,
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
        data: Dict[str, str] = self.extract_data(['name', 'uid', 'broadcaster', 'channel'])  # Get the form data
        users: Reference = self.db('users')  # Get collection

        users.child(data['uid']).set({
                'name': data['name'],
                'broadcaster': data['broadcaster'],
                'channel': data['channel']
            })

        self.write(json.dumps({
                'status_code': 200,
                'message': f'Added {data["name"]} to Database'
            }))


class MessageHandler(BaseHandler):
    async def post(self) -> None:
        data: Dict[str, str] = self.extract_data(['message', 'uid'])  # Get the form data
        users: Reference = self.db("users")  # Get collection

        users_ref: Dict[str, Dict[str, str]] = users.get()
        channel: Reference = self.db(users_ref[data['uid']]['channel'])

        channel.push().set({
            'uid': data['uid'],
            'name': users_ref[data['uid']]['name'],
            'broadcaster': users_ref[data['uid']]['broadcaster'],
            'message': data['message']
        })

        self.write(json.dumps({
            'status_code': 200,
            'message': 'Message added'
        }))


class RaiseHandHandler(BaseHandler):
    async def post(self) -> None:
        data: Dict[str, str] = self.extract_data(['uid'])
        privilege: Reference = self.db('privilege')

        privilege.child(data['uid']).set({
            'accepted': 'false'
        })

        self.write(json.dumps({
            'status_code': 200,
            'message': 'Requested Privilege'
        }))


class AcceptRequestHandler(BaseHandler):
    async def post(self) -> None:
        data: Dict[str, str] = self.extract_data(['uid'])
        privilege: Reference = self.db('privilege')

        user_ref: Dict[str, str] = privilege.child(data['uid']).get()
        is_accepted: str = user_ref['accepted']

        if is_accepted == 'true':
            raise tornado.web.HTTPError(409, reason="User already privileged")

        privilege.child(data['uid']).set({
            'accepted': 'true'
        })

        self.write({
            'status_code': 200,
            'message': f'{data["uid"]} is now privileged'
        })


class RemoveFromListHandler(BaseHandler):
    async def post(self) -> None:
        data: Dict[str, str] = self.extract_data(['uid'])
        privilege: Reference = self.db('privilege')
        privilege.child(data['uid']).delete()

        self.write(json.dumps({
            'status_code': 200,
            'message': f'{data["uid"]} removed'
        }))


if __name__ == "__main__":
    load_dotenv()
    options.parse_command_line()

    cred: Certificate = credentials.Certificate(str(Path(f"./{os.environ['SERVICE_ACCOUNT_FILE']}").resolve()))

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ['DB_URL']
    })

    app: Application = tornado.web.Application(
        handlers=[
            (r"/", PingHandler),
            (r"/auth", AuthHandler),
            (r"/post", MessageHandler),
            (r"/add", RaiseHandHandler),
            (r"/accept", AcceptRequestHandler),
            (r"/delete", RemoveFromListHandler)
        ],
        default_handler_class=my404handler,
        debug=True,
        form_data={},
    )
    http_server: HTTPServer = tornado.httpserver.HTTPServer(app)
    port: int = int(os.environ.get('PORT', options.port))
    print(f"Listening on PORT: {port}")
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()
