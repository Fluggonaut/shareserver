#!/usr/bin/env python3
import unittest
import sys
sys.path.append("..")
import server as restserver
import endpoints.yt as yt


class TestServerMethods(unittest.TestCase):
    def setUp(self):
        pass

    def test_match_endpoints(self):
        server = restserver.RESTServer(("", 8080), restserver.RequestHandler)

        self.assertEqual(server.match_endpoints("/a"), None, "incorrect behavior on empty endpoint list")

        ep_root = restserver.Endpoint("/")
        ep_a = restserver.Endpoint("/a")
        ep_ab = restserver.Endpoint("/a/b")
        ep_ac = restserver.Endpoint("/a/c")
        ep_abc = restserver.Endpoint("/a/b/c")
        ep_adc = restserver.Endpoint("/a/d/c")
        ep_bc = restserver.Endpoint("/b/c")

        server.register_endpoint(ep_a)
        self.assertEqual(server.match_endpoints("/a"), ep_a, "simple positive matching testcase failed")
        self.assertEqual(server.match_endpoints("/b"), None, "simple negative matching testcase failed")

        server.register_endpoint(ep_ab)
        server.register_endpoint(ep_ac)
        server.register_endpoint(ep_abc)
        server.register_endpoint(ep_adc)
        self.assertEqual(server.match_endpoints("/a"), ep_a, "positive matching testcase failed")
        self.assertEqual(server.match_endpoints("/a/b"), ep_ab, "positive matching testcase failed")
        self.assertEqual(server.match_endpoints("/a/b/c/d"), ep_abc, "positive matching testcase failed")
        self.assertEqual(server.match_endpoints("/c"), None, "negative matching testcase failed")
        self.assertEqual(server.match_endpoints("/b"), None, "negative matching testcase failed")

        server.register_endpoint(ep_bc)
        self.assertEqual(server.match_endpoints("/b/a"), None, "negative partial matching testcase failed")

        server.register_endpoint(ep_root)
        self.assertEqual(server.match_endpoints("/"), ep_root, "matching on / failed")
        self.assertEqual(server.match_endpoints("/c"), ep_root, "matching on / failed")


class TestYoutubeMethods(unittest.TestCase):
    def test_link_parser(self):
        self.assertEqual(yt.parse_yt_url("https://www.youtube.com/watch?v=ivroIGMAVig"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("https://www.youtube.com/watch?v=-ivroIGMAVig"), "-ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("https://www.youtube.com/watch?v=ivroIGMAVig&foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("https://www.youtube.com/watch?v=ivroIGMAVig&foo=bar&bar=foo"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("http://www.youtube.com/watch?v=ivroIGMAVig&foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("https://youtube.com/watch?v=ivroIGMAVig&foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("http://youtube.com/watch?v=ivroIGMAVig&foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("www.youtube.com/watch?v=ivroIGMAVig&foo=bar"), "ivroIGMAVig")

        self.assertEqual(yt.parse_yt_url("https://m.youtube.com/watch?v=ivroIGMAVig"), "ivroIGMAVig")

        self.assertEqual(yt.parse_yt_url("https://youtu.be/ivroIGMAVig"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("https://youtu.be/ivroIGMAVig?foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("http://youtu.be/ivroIGMAVig?foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("www.youtu.be/ivroIGMAVig&foo=bar"), "ivroIGMAVig")
        self.assertEqual(yt.parse_yt_url("https://youtube.com/watch?v=-TRRejlAwo8"), "-TRRejlAwo8")

        # Negative tests
        self.assertRaises(yt.ParseError, yt.parse_yt_url, "foo")
        self.assertRaises(yt.ParseError, yt.parse_yt_url, "https://youtube.com/")
        self.assertRaises(yt.ParseError, yt.parse_yt_url, "https://youtube.com/user/foo")
        self.assertRaises(yt.ParseError, yt.parse_yt_url, "https://youtu.be/?foo=bar")
        self.assertRaises(yt.ParseError, yt.parse_yt_url, "https://youtube.com/ivroIGMAVig")


if __name__ == "__main__":
    unittest.main()
