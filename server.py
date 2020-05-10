#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import pkgutil
import sys
import logging


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

        print("About to serve forever")
        self.serve_forever()
        print("Serving forever")

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
                plugin = module.Plugin(self)
                logging.info("Loaded Plugin: {}".format(plugin.name))
            except (AttributeError, TypeError, Exception) as e:
                failed.append(module)
                logging.error("Unable to load plugin: {} ({})".format(module, e))
            else:
                self.plugins[i] = plugin

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
        logging.info("Registered endpoint: {}".format(endpoint.path))

    def shutdown(self):
        for plugin in self.plugins:
            try:
                plugin.shutdown()
            except AttributeError:
                logging.warning("Plugin {} has no shutdown method.".format(plugin))
                pass
            except Exception as e:
                logging.error("Plugin {} failed to shut down ({})".format(plugin, e))

        logging.info("Shutting down ...")
        try:
            self.shutdown()
            logging.info("Shutdown complete. Bye.")
        except Exception as e:
            logging.error("HTTP Server shutdown failed ({})".format(e))


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

        assert(self.path.startswith(self.ep))
        return self.path[len(self.ep):]

    def do_method(self, method):
        logging.debug("Incoming {} on {}".format(method, self.path))

        self.ep = self.server.match_endpoints(self.path)
        if self.ep is None:
            logging.info("No matching endpoint for {} found, sending 404".format(self.path))
            self.send_response(404)  # Not found
            self.end_headers()
            return

        try:
            logging.debug("Sending request to endpoint {}".format(ep.path))
            if method == "GET":
                self.ep.do_GET(self)
            elif method == "POST":
                self.ep.do_POST(self)
            elif method == "PUT":
                self.ep.do_PUT(self)
            elif method == "HEAD":
                self.ep.do_HEAD(self)
            else:
                raise AttributeError
        except AttributeError:
            logging.debug("Endpoint {} does not support method {}, sending 405".format(ep.path, method))
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
