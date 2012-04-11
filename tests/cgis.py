#!/usr/bin/env python
import BaseHTTPServer as base
import CGIHTTPServer as cgi

httpd = base.HTTPServer(('localhost',8183),
                        cgi.CGIHTTPRequestHandler)
httpd.serve_forever()
print 'Done'
