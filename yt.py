from server import Endpoint
from threading import Thread, Lock, Event
import os


###########
# config ##
VIDEODIR = "videos"


class ParseError(Exception):
    pass


class Queue(Thread):
    def __init__(self):
        self.lock = Lock()
        self.queue = []
        self.update_event = Event()
        super().__init__()

    def append(self, el):
        with self.lock:
            self.queue.append(el)
        self.update_event.set()


class Downloader(Queue):
    def __init__(self, player):
        self.player = player
        super().__init__()

    def download(self, videoid):
        # "youtube-dl {} -o {}/%(id)s.%(ext)s".format(videoid, dir)
        pass

    def run(self):
        self.update_event.wait()
        with self.lock:
            pass


class Player(Queue):
    def run(self):
        self.update_event.wait()
        with self.lock:
            pass


class SimpleEndpoint(Endpoint):
    def do_GET(self, reqhandler):
        print("Incoming GET on {}".format(reqhandler.path))

    def do_POST(self, reqhandler):
        print("Incoming POST on {}".format(reqhandler.path))
        clen = int(reqhandler.headers['Content-Length'])
        data = reqhandler.rfile.read(clen)
        print("POST data: {}".format(data))


def parse_yt_url(url):
    """
    Extracts yt video id from url. Raises ParseError if no video id can be found.
    :param url: URL to be parsed
    :return: video id
    """



def init(rest_server):
    endpoint = SimpleEndpoint("/")
    rest_server.register_endpoint(endpoint)
