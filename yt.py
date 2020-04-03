from server import Endpoint
from threading import Thread, Lock, Event
import os


###########
# config ##
VIDEODIR = "videos"


class ParseError(Exception):
    pass


class DownloadError(Exception):
    pass


class PlayerError(Exception):
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
    def __init__(self, videodir, player):
        """
        Download handler. Use append() to request a download; calls player.append() on download success.
        :param videodir: Directory where the videos are to be stored
        :param player: Player object
        """
        self.videodir = videodir
        if self.videodir.endswith("/"):
            self.videodir = self.videodir[:-1]
        self.player = player
        self.storage = []
        self.scan_storage()
        super().__init__()
        self.start()

    def scan_storage(self):
        """
        Scans videodir for video files; works like a download cache.
        Video files are expected to be named videoid.ext with ext being the file extension.
        """
        self.storage = []
        for el in os.listdir(self.videodir):
            self.storage.append(os.path.splitext(self.videodir + "/" + el))

    def download(self, videoid):
        """
        Downloads yt video videoid to videodir/videoid.ext. Raises DownloadError when youtube-dl fails.
        :param videoid: yt id of the video to be downloaded
        """
        found = False
        for file, ext in self.storage:
            if file == videoid:
                found = True
                break

        if not found:
            retval = os.system("youtube-dl {} -o {}/%(id)s.%(ext)s".format(videoid, self.videodir))
            if retval != 0:
                raise DownloadError("youtube-dl failed")
            self.scan_storage()

        found = False
        for file, ext in self.storage:
            if file == videoid:
                found = True
                self.player.append(file + "." + ext)
        if not found:
            raise DownloadError("file not found after download: {}".format(videoid))

    def run(self):
        self.update_event.wait()
        with self.lock:
            for el in self.queue:
                self.download(el)
            self.update_event.clear()


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
