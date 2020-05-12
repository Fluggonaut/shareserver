#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock
from datetime import datetime
from util import Stack
import pkgutil
import sys
import logging
import json


############
# config ###
PORT = 8080
DEBUG = False
PLUGINDIR = "endpoints"

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


class MethodError(Exception):
    pass


class Error:
    def __init__(self, endpoint, msg, ts=None):
        self.msg = msg
        self.endpoint = endpoint
        self.timestamp = None
        if ts is not None:
            self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "plugin": self.endpoint,
            "msg": self.msg,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class Endpoint:
    """
    Endpoint to be subclassed and registered with the server.
    Methods that are called on appropriate request:
    do_GET(requesthandler),
    do_POST(requesthandler),
    do_HEAD(requesthandler),
    do_PUT(requesthandler)
    If a method is not present, the request is refused (TODO 403 or 404 maybe).
    """
    def __init__(self, path):
        self.path = sanitize_path(path)
        self.pathlist = self.path.split("/")  # todo property structure


class RESTServer(HTTPServer):
    def __init__(self, config, **kwargs):
        addr = ("", config["port"])
        super().__init__(addr, RequestHandler, **kwargs)

        self.endpoints = []
        self.plugins = []
        self.load_plugins()

        self._endpoints_to_register = None
        self._errors = Stack()
        self._error_lock = Lock()

        logging.info("Running server.")
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            self.shutdown()

    def load_plugins(self):
        # import
        for el in pkgutil.iter_modules([PLUGINDIR]):
            plugin = el[1]
            try:
                p = pkgutil.importlib.import_module("{}.{}".format(PLUGINDIR, plugin))
            except Exception as e:
                logging.error("Unable to load plugin: {} ({})".format(plugin, e))
                continue
            else:
                self.plugins.append(p)

        # load
        failed = []
        for i in range(len(self.plugins)):
            module = self.plugins[i]
            try:
                self._endpoints_to_register = []
                plugin = module.Plugin(self)
                logging.info("Loaded Plugin: {}".format(plugin.name))
            except (AttributeError, TypeError, Exception) as e:
                failed.append(module)
                logging.error("Unable to load plugin: {} ({})".format(module, e))
                continue

            self.plugins[i] = plugin
            for endpoint in self._endpoints_to_register:
                self.endpoints.append((endpoint, plugin))
                logging.info("Registered endpoint: {}".format(endpoint.path))
            self._endpoints_to_register = None

        for el in failed:
            self.plugins.remove(el)

    def match_endpoints(self, path):
        """
        Finds the endpoint that matches best with path.
        If path is "/a/b/c", it matches "/a/b" better than "/a". It does not match "/b".
        :param path: path that is to be matched
        :return: endpoint object that matches; None if no match is found
        """
        path = sanitize_path(path).split("/")
        candidates = []
        for el in self.endpoints:
            candidates.append(el[0])
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
        if self._endpoints_to_register is None:
            logging.error("Endpoints must be registered in the Plugin constructor ({})".format(endpoint.path))
            return
        if endpoint not in self.endpoints and endpoint not in self._endpoints_to_register:
            self._endpoints_to_register.append(endpoint)
        else:
            logging.error("Endpoint already registered: {}".format(endpoint.path))

    def report_error(self, endpoint, msg, timestamp=None):
        """
        Reports an error to the server error stack.
        :param endpoint: Endpoint object the error occured in.
        :param msg: Error message.
        :param timestamp: Error timestamp; uses now if ommited.
        :return:
        """
        error = Error(endpoint, msg, timestamp)
        self._error_lock.acquire()
        self._errors.push(error)
        self._error_lock.release()

    def consume_errors(self):
        """
        Generator for all errors on the server error stack. Errors are removed from the stack (popped).
        """
        self._error_lock.acquire()
        while True:
            try:
                yield self._errors.pop()
            except IndexError:
                break
        self._error_lock.release()

    def consume_error(self):
        """
        Pops one error from the server error stack (read and remove).
        :return: Last error
        """
        self._error_lock.acquire()
        r = self._errors.pop()
        self._error_lock.release()
        return r

    def has_error(self):
        return not self._errors.is_empty()

    def last_error(self):
        """
        Reads the last error from the error stack. Does not remove it.
        :return: Last error
        """
        self._error_lock.acquire()
        r = self._errors.top()
        self._error_lock.release()
        return r

    def shutdown(self):
        for plugin in self.plugins:
            try:
                plugin.shutdown()
            except AttributeError:
                logging.info("Plugin {} has no shutdown method.".format(plugin))
                pass
            except Exception as e:
                logging.error("Plugin {} failed to shut down ({})".format(plugin, e))

        logging.info("Shutting down.")
        try:
            self.shutdown()
        except Exception as e:
            logging.error("Clean shutdown failed ({})".format(e))


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.ep = None
        self._route = None
        super().__init__(*args, **kwargs)

    @property
    def route(self):
        if self._route is not None:
            return self._route
        if self.ep is None:
            return None

        assert(self.path.startswith(self.ep.path))
        return self.path[len(self.ep.path):]

    def do_method(self, method):
        logging.debug("Incoming {} on {}".format(method, self.path))

        self.ep = self.server.match_endpoints(self.path)
        if self.ep is None:
            logging.info("No matching endpoint for {} found, sending 404".format(self.path))
            self.send_response(404)  # Not found
            self.end_headers()
            return

        try:
            logging.debug("Sending request to endpoint {}".format(self.ep.path))
            if method == "GET":
                self.ep.do_GET(self)
            elif method == "POST":
                self.ep.do_POST(self)
            elif method == "PUT":
                self.ep.do_PUT(self)
            elif method == "HEAD":
                self.ep.do_HEAD(self)
            else:
                raise MethodError
        except MethodError:
            logging.debug("Endpoint {} does not support method {}, sending 405".format(self.ep.path, method))
            self.send_response(405)  # Method not allowed
            self.end_headers()

    def do_POST(self):
        self.do_method("POST")

    def do_GET(self):
        self.do_method("GET")

    def do_PUT(self):
        self.do_method("PUT")

    def do_HEAD(self):
        self.do_method("HEAD")


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
        if args[i] == "--port":
            try:
                config["port"] = int(args[i+1])
            except KeyError:
                raise IndexError("Port not specified.")
            except ValueError:
                raise ParseError("{} is not a valid port number.".format(args[i+1]))
            i += 1
        elif args[i] == "--debug":
            config["debug"] = True
        elif args[i] == "--help":
            config["help"] = True
        elif args[i] == "--yttest":
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
        logging.debug("Loglevel: Debug")
    else:
        logging.basicConfig(level=logging.WARNING)

    RESTServer(config)


if __name__ == "__main__":
    main(sys.argv)
