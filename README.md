A simple REST server that accepts Youtube links, downloads the corresponding video via youtube-dl and plays them via omxplayer.

Easily expandable to support other endpoints.

The http server is probably unsafe, do not point it towards the internet.

# TODO
* Daemonize
* Nice termination
* Improve logging
* Plugin structure for endpoints
* Fix tests
* Improve test coverage

# Features that would be great
* Playback control
* Stream instead of download
