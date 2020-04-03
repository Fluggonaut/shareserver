#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import logging


# config ###
PORT = 8080
DEBUG = False
#######

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

    def match_endpoints(self, path):

    def register_endpoint(self, endpoint):
        """
        :param endpoint: Endpoint object
        """
        self.endpoints.append(endpoint)


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("Received POST; path: {}".format(self.path))
        print("Posted data:\n{}".format(post_data))

    def do_GET(self):
        print("Received GET; path: {}".format(self.path))


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
    config = parse_args(args)
    if config["help"]:
        print(usage)
        return
    elif config["debug"]:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    run_server(config["port"])

if __name__ == "__main__":
    main(sys.argv)
