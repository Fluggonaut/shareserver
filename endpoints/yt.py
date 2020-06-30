from server import Endpoint
from threading import Thread, Lock, Event
from enum import Enum
import logging
import os
import re
import json
import subprocess


###########
# config ##
VIDEODIR = "videos"
DEFAULTVOL = -3300
#######

"""
Endpoint:
GET /linkshare
    Payload:
    {"link": <youtubelink>}
"""


class ParseError(Exception):
    pass


class DownloadError(Exception):
    pass


class PlayerError(Exception):
    pass


class Plugin:
    def __init__(self, rest_server):
        self.name = "yt"
        self.server = rest_server

        logging.info("Setting up yt plugin ...")
        player = Player(self)
        downloader = Downloader(VIDEODIR, player, self)
        streamer = Streamer(VIDEODIR, player, self)
        self.endpoint = LinkshareEndpoint("/linkshare", downloader, streamer, self)
        rest_server.register_endpoint(self.endpoint)

    def report_error(self, msg):
        self.server.report_error(self, msg)


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


class StreamPlayer(Thread):
    def __init__(self, url, plugin=None, videoid=None, name=None):
        self.url = url
        self.plugin = plugin
        self.videoid = videoid
        self.name = name
        super().__init__()

    def run(self):
        cmd = ["omxplayer", "--vol", str(DEFAULTVOL), self.url]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0:
            msg = "{} omxplayer failed on {} with error {}".format(self.name, self.videoid, proc.stdout.decode("utf-8"))
            logging.warning(msg)
            if self.plugin:
                self.plugin.report_error(msg)


class Streamer(Queue):
    def __init__(self, videodir, player, plugin=None):
        """
        Streaming player. Use append() to request a stream.
        :param videodir: Not used
        :param player: Player object
        :param plugin: Plugin object to report errors to. Can be omitted.
        """
        self.plugin = plugin
        super().__init__()

    def append(self, videoid):
        logging.info("Added {} to streaming queue".format(videoid))
        super().append(videoid)

    def consume(self, videoid):
        """
        Overrides super method. Streams video videoid.
        """
        stdout = subprocess.run(["youtube-dl", "-g", videoid], capture_output=True).stdout.decode("utf-8").split("\n")
        if len(stdout) != 3:
            self.plugin.report_error("youtube-dl -g failed on {}".format(videoid))
            raise DownloadError
        video, audio = stdout[:-1]
        video = StreamPlayer(video, plugin=self.plugin, videoid=videoid, name="Video")
        audio = StreamPlayer(audio, plugin=self.plugin, videoid=videoid, name="Audio")
        video.start()
        audio.start()


class Downloader(Queue):
    def __init__(self, videodir, player, plugin=None):
        """
        Download handler. Use append() to request a download; calls player.append() on download success.
        :param videodir: Directory where the videos are to be stored
        :param player: Player object
        :param plugin: Plugin object to report errors to. Can be omitted.
        """
        self.videodir = videodir
        if self.videodir.endswith("/"):
            self.videodir = self.videodir[:-1]
        self.player = player
        self.plugin = plugin
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
            file, ext = os.path.splitext(self.videodir + "/" + el)
            _, file = os.path.split(file)
            self.storage.append((file, ext))

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
            retval = os.system("youtube-dl {} -f bestvideo[ext=mp4]+bestaudio[ext=m4a] -o {}/%\(id\)s.%\(ext\)s"
                               .format("https://youtube.com/watch?v=" + videoid, self.videodir))
            if retval != 0:
                msg = "youtube-dl failed on {}".format(videoid)
                logging.warning(msg)
                if self.plugin:
                    self.plugin.report_error(msg)
                return
            self.scan_storage()

        found = False
        for file, ext in self.storage:
            if file == videoid:
                found = True
                self.player.append(self.videodir + "/" + file + ext)
        if not found:
            msg = "file not found after download: {}".format(videoid)
            if self.plugin:
                self.plugin.report_error(msg)
            logging.warning(msg)
            return


class Player(Queue):
    def __init__(self, plugin=None):
        """
        :param plugin: Plugin object to report errors to. Can be omitted.
        """
        self.plugin = plugin
        super().__init__()

    def consume(self, videofile):
        logging.info("Playing {}".format(videofile))
        retval = os.system("omxplayer --vol {} {}".format(DEFAULTVOL, videofile))
        if retval != 0:
            msg = "omxplayer failed on {}".format(videofile)
            logging.warning(msg)
            if self.plugin:
                self.plugin.report_error(msg)

    def append(self, videofile):
        logging.info("Added {} to player queue".format(videofile))
        super().append(videofile)


class Mode(Enum):
    DOWNLOAD = 0
    STREAM = 1


class LinkshareEndpoint(Endpoint):
    def __init__(self, path, downloader, streamer, plugin):
        self.downloader = downloader
        self.streamer = streamer
        self.plugin = plugin
        self.mode = Mode.DOWNLOAD
        self.operator = self.downloader
        super().__init__(path)

    def do_GET(self, reqhandler):
        route = reqhandler.route.split("/")
        if len(route) > 0 and route[0] == "":
            route = route[1:]

        # Report mode
        if len(route) == 0:
            found = None
            if self.mode == Mode.DOWNLOAD:
                found = "Download"
            elif self.mode == Mode.STREAM:
                found = "Stream"
            if not found:
                reqhandler.send_response(500)
                reqhandler.end_headers()
                return
            else:
                reqhandler.send_response(200)
                reqhandler.end_headers()
                reqhandler.wfile.write(found.encode("utf-8"))
                return

        # Change mode
        if len(route) != 1 or route[0] not in ["download", "stream"]:
            reqhandler.send_response(400)  # Bad Request
            reqhandler.end_headers()
            return
        else:
            if route[0] == "download":
                self.mode = Mode.DOWNLOAD
                self.operator = self.downloader
            elif route[0] == "stream":
                self.mode = Mode.STREAM
                self.operator = self.streamer
            else:
                reqhandler.send_response(500)
                reqhandler.end_headers()
                return
            reqhandler.send_response(200)
            reqhandler.end_headers()
            return

    def do_POST(self, reqhandler):
        logging.debug("Incoming POST on {}".format(reqhandler.path))
        try:
            clen = int(reqhandler.headers['Content-Length'])
        except KeyError:
            reqhandler.send_response(411)  # Length required
            reqhandler.end_headers()
            return
        post = reqhandler.rfile.read(clen)
        logging.debug("POST data: {}".format(post))
        try:
            data = json.loads(post)
        except json.decoder.JSONDecodeError:
            logging.warning("Invalid JSON: {}".format(post))
            reqhandler.send_response(400)  # Bad Request
            reqhandler.end_headers()
            return

        try:
            link = data["link"]
        except (KeyError, TypeError):
            msg = "link not found in {}".format(data)
            logging.warning(msg)
            self.plugin.report_error(msg)
            reqhandler.send_response(422)  # Unprocessable entity
            reqhandler.end_headers()
            return
        try:
            link = parse_yt_url(link)
        except ParseError:
            msg = "Unknown Youtube link: {}".format(link)
            logging.warning(msg)
            self.plugin.report_error(msg)
            reqhandler.send_response(422)  # Unprocessable entity
            reqhandler.end_headers()
            return
        self.operator.append(link)
        reqhandler.send_response(202)  # Accepted
        reqhandler.end_headers()


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
    m1 = re.match(r"(https?://)?(www.)?(m.)?youtube.com/watch\?v=(?P<videoid>[^&/]+)", url)

    # https://youtu.be/videoid&foo=bar
    m2 = re.match(r"(https?://)?(www.)?youtu.be/(?P<videoid>[^?&/]+)", url)

    if m1 is not None:
        return m1.group("videoid")
    if m2 is not None:
        return m2.group("videoid")
    raise ParseError()
