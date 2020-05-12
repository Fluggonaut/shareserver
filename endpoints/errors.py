from server import Endpoint
import logging
import json


class ErrorReporting(Endpoint):
    def do_GET(self, reqhandler):
        route = reqhandler.route.split("/")
        server = reqhandler.server
        if len(route) > 0 and route[0] == "":
            route = route[1:]
        if len(route) > 0 and route[-1] == "":
            route = route[:-1]

        if len(route) < 1:
            logging.info("Incorrect error reporting access: {}".format(reqhandler.route))
            reqhandler.send_response(404)  # Not found
            reqhandler.end_headers()
            return

        report = []
        if route[0] == "all":
            for el in server.consume_errors():
                report.append(el.serializable())
        elif route[0] == "last":
            if server.has_error():
                report.append(server.last_error().serializable())
        else:
            logging.info("Incorrect error reporting access: {}".format(reqhandler.route))
            reqhandler.send_response(404)  # Not found
            reqhandler.end_headers()
            return

        reqhandler.send_response(200)  # OK
        reqhandler.end_headers()
        reqhandler.wfile.write(json.dumps(report).encode("utf-8"))
        return


class Plugin:
    def __init__(self, rest_server):
        self.name = "errors"
        endpoint = ErrorReporting("sys/errors")
        rest_server.register_endpoint(endpoint)
