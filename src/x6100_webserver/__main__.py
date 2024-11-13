import argparse

import bottle
import bottle.ext.sqlite

from . import apps


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="path to SQLite3 database", required=True)
    parser.add_argument("--host", help="ip address to listen", default="localhost")
    parser.add_argument("--port", type=int, help="port to listen", default=8080)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    plugin = bottle.ext.sqlite.Plugin(dbfile=args.db, keyword="dbcon")
    apps.app.install(plugin)
    apps.app.run(host=args.host, port=args.port, debug=args.debug)

run()
