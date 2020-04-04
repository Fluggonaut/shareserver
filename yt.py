from server import Endpoint
from threading import Thread, Lock, Event
import logging
import os
import re
import json


###########
# config ##
VIDEODIR = "videos"
#######


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
        self.start()

    def consume(self, el):
        """
        Is called for every element that is appended to the queue.
        :param el: Element that was appended to the queue.
        """
        raise NotImplementedError()

    def append(self, el):
        with self.lock:
            self.queue.append(el)
        self.update_event.set()

    def run(self):
        while True:
            self.update_event.wait()
            with self.lock:
                to_consume = self.queue
                self.queue = []
                self.update_event.clear()
            for el in to_consume:
                self.consume(el)


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

        # mkdir videodir
        if os.path.exists(self.videodir):
            if not os.path.isdir(self.videodir):
                raise NotADirectoryError(self.videodir)
        else:
            os.mkdir(self.videodir)

        self.scan_storage()

        super().__init__()

    def append(self, videoid):
        logging.info("Added {} to download queue".format(videoid))
        super().append(videoid)

    def scan_storage(self):
        """
        Scans videodir for video files; works like a download cache.
        Video files are expected to be named videoid.ext with ext being the file extension.
        """
        self.storage = []
        for el in os.listdir(self.videodir):
            self.storage.append(os.path.splitext(self.videodir + "/" + el))

    def consume(self, videoid):
        """
        Overrides super method.
        Downloads yt video videoid to videodir/videoid.ext. Raises DownloadError when youtube-dl fails.
        :param videoid: yt id of the video to be downloaded
        """
        found = False
        for file, ext in self.storage:
            if file == videoid:
                found = True
                break

        if not found:
            logging.info("Downloading {}".format(videoid))
            retval = os.system("youtube-dl {} -o {}/%(id)s.%(ext)s".format(videoid, self.videodir))
            if retval != 0:
                msg = "youtube-dl failed on {}".format(videoid)
                logging.error(msg)
                raise DownloadError(msg)
            self.scan_storage()

        found = False
        for file, ext in self.storage:
            if file == videoid:
                found = True
                self.player.append(file + "." + ext)
        if not found:
            raise DownloadError("file not found after download: {}".format(videoid))


class Player(Queue):
    def consume(self, videofile):
        logging.info("Playing {}".format(videofile))
        os.system("omxplayer --vol -3300 {}".format(videofile))

    def append(self, videofile):
        logging.info("Added {} to player queue".format(videofile))
        super().append(videofile)


class LinkshareEndpoint(Endpoint):
    def __init__(self, path, downloader):
        self.downloader = downloader
        super().__init__(path)

    def do_POST(self, reqhandler):
        print("Incoming POST on {}".format(reqhandler.path))
        clen = int(reqhandler.headers['Content-Length'])
        post = reqhandler.rfile.read(clen)
        try:
            data = json.loads(post)
        except json.decoder.JSONDecodeError:
            logging.warning("Invalid JSON: {}".format(post))
            return

        try:
            link = data["link"]
        except KeyError:
            logging.warning("link not found in {}".format(data))
            return
        self.downloader.append(link)


def parse_yt_url(url):
    """
    Extracts yt video id from url. Raises ParseError if no video id can be found.
    Currently supports:
    [http[s]://][www.]youtube.com/watch?v=videoid[&foo]
    [http[s]://][www.]youtu.be/videoid[?foo]
    :param url: URL to be parsed
    :return: video id
    """
    url = url.strip()

    # https://www.youtube.com/watch?v=videoid&foo=bar
    m1 = re.match(r"(https?://)?(www.)?youtube.com/watch\?v=(?P<videoid>[^&/]+)", url)

    # https://youtu.be/videoid&foo=bar
    m2 = re.match(r"(https?://)?(www.)?youtu.be(?P<videoid>[^&/s]+)", url)

    if m1 is not None:
        return m1.group("videoid")
    if m2 is not None:
        return m2.group("videoid")
    logging.warning("Unknown Youtube link: {}".format(url))
    raise ParseError()


def init(rest_server):
    player = Player()
    downloader = Downloader(VIDEODIR, player)
    endpoint = LinkshareEndpoint("/linkshare", downloader)
    rest_server.register_endpoint(endpoint)
