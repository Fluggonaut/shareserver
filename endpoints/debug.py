from server import Endpoint


class SimpleEndpoint(Endpoint):
    def do_GET(self, reqhandler):
        print("Incoming GET on {}".format(reqhandler.path))

    def do_POST(self, reqhandler):
        print("Incoming POST on {}".format(reqhandler.path))
        clen = int(reqhandler.headers['Content-Length'])
        data = reqhandler.rfile.read(clen)
        print("POST data: {}".format(data))


class Plugin:
    def __init__(self, rest_server):
        self.name = "debug"
        endpoint = SimpleEndpoint("/")
        # rest_server.register_endpoint(endpoint)
