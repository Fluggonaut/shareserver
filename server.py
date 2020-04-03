#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import logging


# config ###
PORT = 8080
DEBUG = False
#######

_loglevel = None

usage = "Usage: {} [OPTIONS]\n\n" \
        "OPTIONS:\n" \
        "  --help\n" \
        "  --port PORT\n" \
        "  --debug\n" \
        "  --yttest YOUTUBELINK\n" \
        "".format(sys.argv[0])


class ParseError(Exception):
    pass


class Endpoint:
    def __init__(self, path):
        self.path = path


class RESTServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        self.endpoints = []
        super().__init__(*args, **kwargs)

    def register_endpoint(self, endpoint):
        """
        :param endpoint: Endpoint object
        """
        self.endpoints.append(endpoint)


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global _loglevel
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)


def run_server(port):
    addr = ("", port)
    RESTServer(addr, RequestHandler).serve_forever()


def parse_args(args):
    config = {
        "help": False,
        "port": PORT,
        "debug": DEBUG,
        "yttest": False,
        "yttestlink": None,
    }

    i = 1
    while i < len(args):
        if args[i] == "port":
            try:
                config["port"] = int(args[i+1])
            except KeyError:
                raise IndexError("Port not specified.")
            except ValueError:
                raise ParseError("{} is not a valid port number.".format(args[i+1]))
            i += 1
        elif args[i] == "debug":
            config["debug"] = True
        elif args[i] == "help":
            config["help"] = True
        elif args[i] == "yttest":
            config["yttest"] = True
            try:
                config["yttestlink"] = args[i+1]
            except IndexError:
                raise ParseError("Youtube link not specified.")
            i += 1
        i += 1

    return config


def main(args):
    global _loglevel

    config = parse_args(args)
    if config["help"]:
        print(usage)
        return
    elif config["debug"]:
        _loglevel = "debug"
    
    run_server(config["port"])

if __name__ == "__main__":
    main(sys.argv)
