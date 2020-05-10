from server import Endpoint
import logging
import os

RCSWITCHCMD = "rcswitch"


class RCEndpoint(Endpoint):
    def do_GET(self, reqhandler):
        print("Incoming GET on {}".format(reqhandler.path))
        route = reqhandler.route.split("/")
        if route[0] == "" and len(route) > 1:
            route = route[1:]

        if len(route) < 2:
            logging.info("Incorrect rswitch access: {}".format(reqhandler.route))
        route[0] = route[0].lower()
        route[1] = route[1].lower()
        if route[0].lower() not in ["a", "b", "c", "d", "all"]:
            logging.warning("Invalid channel: {}".format(route[0]))
            reqhandler.send_response(400)  # Bad Request
            reqhandler.end_headers()
            return
        if route[1] not in ["on", "off"]:
            logging.info("Invalid toggle value: {}".format(route[1]))
            reqhandler.send_response(400)  # Bad Request
            reqhandler.end_headers()
            return

        if route[0] is "all":
            for el in ["a", "b", "c", "d"]:
                rcswitch(el, route[1])
        else:
            rcswitch(route[0], route [1])

        reqhandler.send_response(202)  # Accepted
        reqhandler.end_headers()


class Plugin:
    def __init__(self, rest_server):
        self.name = "rcswitch"
        endpoint = RCEndpoint("rcswitch")
        rest_server.register_endpoint(endpoint)

def rcswitch(channel, toggle):
    os.system("{} {} {}".format(RCSWITCHCMD, channel, toggle))
