from server import Endpoint
import logging


class ErrorReporting(Endpoint):
    def do_GET(self, reqhandler):
        route = reqhandler.route.split("/")
        if len(route) > 0 and route[0] == "":
            route = route[1:]
        if len(route) > 0 and route[-1] == "":
            route = route[:-1]

        if len(route) < 1:
            logging.info("Incorrect error reporting access: {}".format(reqhandler.route))
            reqhandler.send_response(404)  # Not found
            reqhandler.end_headers()
            return

        if route[1] == "all":
            report = []
            for el in reqhandler.server.consume_errors():
                report.append(str(el))
            reqhandler.server.wfile.write(report)
        elif route[1] == "last":
            last = reqhandler.server.errors.pop()
            reqhandler.server.wfile.write(last)
        else:
            logging.info("Incorrect error reporting access: {}".format(reqhandler.route))
            reqhandler.send_response(404)  # Not found
            reqhandler.end_headers()
            return

        reqhandler.send_response(200)  # OK
        reqhandler.end_headers()
        return


class Plugin:
    def __init__(self, rest_server):
        self.name = "errors"
        endpoint = ErrorReporting("sys/errors")
        rest_server.register_endpoint(endpoint)
