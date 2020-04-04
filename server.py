#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import logging

import yt


############
# config ###
PORT = 8080
DEBUG = False

# Endpoint URL options
IGNORE_DOUBLE_SLASH = False  # not implemented yet
CASE_SENSITIVE = False  # not implemented yet
############
############

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
    """
    Endpoint to be subclassed and registered with the server.
    Methods that are called on appropriate request:
    do_GET(requesthandler), do_POST(requesthandler)
    If a method is not present, the request is refused (TODO 403 or 404 maybe).
    """
    def __init__(self, path):
        self.path = sanitize_path(path)
        self.pathlist = self.path.split("/")  # todo property structure


class RESTServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        self.endpoints = []
        super().__init__(*args, **kwargs)

    def match_endpoints(self, path):
        """
        Finds the endpoint that matches best with path.
        If path is "/a/b/c", it matches "/a/b" better than "/a". It does not match "/b".
        :param path: path that is to be matched
        :return: endpoint object that matches; None if no match is found
        """
        path = sanitize_path(path).split("/")
        candidates = self.endpoints.copy()
        matches = []
        todel = []

        # comparison loop
        for i in range(len(path)):
            if not candidates:
                break
            for el in candidates:
                if len(el.pathlist) == i:
                    matches.append(el)
                    todel.append(el)
                elif el.pathlist[i] != path[i]:
                    todel.append(el)
                elif i == len(el.pathlist) - 1:
                    matches.append(el)

            for el in todel:
                candidates.remove(el)
            todel = []

        if not matches:
            return None

        # get best match
        best = matches[0]
        for el in matches:
            if len(el.pathlist) > len(best.pathlist):
                best = el
        return best

    def register_endpoint(self, endpoint):
        """
        Registers and endpoint.
        :param endpoint: Endpoint object
        """
        self.endpoints.append(endpoint)


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        ep = self.server.match_endpoints(self.path)
        ep.do_POST(self)

    def do_GET(self):
        ep = self.server.match_endpoints(self.path)
        ep.do_GET(self)


def sanitize_path(path):
    """
    Removes trailing / and adds leading /; e.g. "/endpoint/path"
    :param path: path to sanitize
    :return: sanitized path
    """
    if not path.startswith("/"):
        path = "/" + path
    if path.endswith("/"):
        path = path[:-1]
    return path


def run_server(port):
    addr = ("", port)
    rest_server = RESTServer(addr, RequestHandler)
    yt.init(rest_server)
    rest_server.serve_forever()


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
