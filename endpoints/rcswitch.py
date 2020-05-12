from server import Endpoint
import logging
import os

RCSWITCHCMD = "rcswitch"


class RCEndpoint(Endpoint):
    def do_GET(self, reqhandler):
        route = reqhandler.route.split("/")
        if route[0] == "" and len(route) > 1:
            route = route[1:]

        if len(route) < 2:
            logging.info("Incorrect rswitch access: {}".format(reqhandler.route))
            reqhandler.send_response(404)  # Not found
            reqhandler.end_headers()
            return
        route[0] = route[0].lower()
        route[1] = route[1].lower()
        if route[0].lower() not in ["a", "b", "c", "d"]:
            logging.warning("Invalid channel: {}".format(route[0]))
            reqhandler.send_response(400)  # Bad Request
            reqhandler.end_headers()
            return
        if route[1] not in ["on", "off"]:
            logging.info("Invalid toggle value: {}".format(route[1]))
            reqhandler.send_response(400)  # Bad Request
            reqhandler.end_headers()
            return

        r = os.system("{} {} {}".format(RCSWITCHCMD, route[0], route[1]))

        reqhandler.send_response(202)  # Accepted
        reqhandler.end_headers()


class Plugin:
    def __init__(self, rest_server):
        self.name = "rcswitch"
        endpoint = RCEndpoint("rcswitch")
        rest_server.register_endpoint(endpoint)
