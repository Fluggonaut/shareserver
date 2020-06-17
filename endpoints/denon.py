import logging
import socket

from server import Endpoint


# CONFIG ###
DENONIP = "192.168.0.3"
DENONPORT = 23  # telnet
############

"""
Endpoints:
GET denon/switch/<toggle>
    toggle out of [on, off]
GET denon/source/<inputsource>
    inputsource out of [rpi, pc]
"""


def send_denon(payload):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((DENONIP, DENONPORT))
        s.sendall(payload)


def switch(toggle):
    r = 404
    if toggle == "on":
        send_denon(b"PWON")
        r = 200
    elif toggle == "off":
        send_denon(b"PWSTANDBY\nZ2OFF")
        r = 200
    return r


def source(inputsource):
    m = {
        "rpi": b"SIMPLAY",
        "pc": b"SIBD",
        "tv": b"SITV",
    }
    r = 404
    if inputsource in m:
        send_denon(m[inputsource])
        r = 200
    return r


class SimpleEndpoint(Endpoint):
    def __init__(self, server, path):
        self.server = server
        super().__init__(path)

    def do_GET(self, reqhandler):
        route = reqhandler.route.split("/")
        if len(route) > 0 and route[0] == "":
            route = route[1:]

        if len(route) < 2:
            logging.info("Incorrect denon access: {}".format(reqhandler.route))
            reqhandler.send_response(404)  # Not found
            reqhandler.end_headers()
            return
        route[0] = route[0].lower()
        route[1] = route[1].lower()
        r = 404
        try:
            if route[0] == "switch":
                r = switch(route[1])
            elif route[0] == "source":
                r = source(route[1])
        except Exception as e:
            self.server.report_error(self, str(e))
            r = 500  # internal server error
        reqhandler.send_reponse(r)
        reqhandler.end_headers()


class Plugin:
    def __init__(self, rest_server):
        self.name = "debug"
        endpoint = SimpleEndpoint(rest_server, "/denon")
        rest_server.register_endpoint(endpoint)
