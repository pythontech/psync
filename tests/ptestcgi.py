#=======================================================================
#       $Id: ptestcgi.py,v 1.2 2011/02/03 12:59:31 pythontech Exp $
#=======================================================================
import CGIHTTPServer
import BaseHTTPServer
import os
import subprocess
import mimetools
import urllib
import cStringIO

__version__ = '$Revision: 1.2 $'.split()[1]

safe_env = {'PATH':'/bin:/usr/bin'}

class PTestCGIHandler(CGIHTTPServer.CGIHTTPRequestHandler):
    '''Modification of CGIHttpRequestHandler which implements
    CGI properly, at least for the psync test suite.
    '''

    server_version = 'PTestCGI/' + __version__

    def is_cgi(self):
        # Given e.g. "/cgi%2Dbin/foo/bar/baz?a=b"
        # set cgi_dir = "/cgi-bin"
        #     cgi_script = "foo"
        #     path_info = "/bar/baz"
        #     query = "a=b"
        i = self.path.find('?')
        if i >= 0:
            mpath = self.path[:i]
            self.query = self.path[i+1:]
        else:
            mpath = self.path
            self.query = None
        ndsi = mpath.split('/',3)
        if len(ndsi) >= 3  and  ndsi[0]=='':
            dir = '/' + urllib.unquote(ndsi[1])
            if dir in self.cgi_directories:
                self.cgi_dir = dir
                self.cgi_script = urllib.unquote(ndsi[2])
                if len(ndsi) > 3:
                    self.path_info = '/'+ndsi[3]
                else:
                    self.path_info = None
                return True
        return False

    def run_cgi(self):
        '''Execute a CGI script.'''
        assert(self.have_fork)
        scriptfile = os.path.join('.', self.cgi_dir[1:], self.cgi_script)
        if not os.path.exists(scriptfile):
            self.send_error(404, "No such CGI script (%s)" % repr(scriptfile))
            return
        if not os.path.isfile(scriptfile):
            self.send_error(403, "CGI script is not a plain file (%s)" %
                            repr(scriptfile))
            return
        if not self.is_executable(scriptfile):
            self.send_error(403, "CGI script is not executable (%s)" %
                            repr(scriptfile))
            return
        #env = {}
        env = os.environ.copy()
        # AUTH_TYPE ?if-auth
        # CONTENT_LENGTH ?if-request_body
        # CONTENT_TYPE ?if-request-body default="application/octet-stream"
        #   DOCUMENT_ROOT
        # GATEWAY_INTERFACE "CGI/1.1"
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        # HTTP_*
        for hdr in self.headers.keys():
            if hdr not in ('content-length',):
                val = ' '.join(self.headers.getheaders(hdr))
                env['HTTP_'+hdr.upper().replace('-','_')] = val
        #   PATH
        # PATH_INFO
        if self.path_info is not None:
            env['PATH_INFO'] = self.path_info
            # PATH_TRANSLATED
        # QUERY_STRING default=""
        if self.query is not None:
            env['QUERY_STRING'] = self.query
        # REMOTE_ADDR
        env['REMOTE_ADDR'] = self.client_address[0]
        # REMOTE_HOST
        #   REMOTE_PORT
        env['REMOTE_PORT'] = str(self.client_address[1])
        # REMOTE_IDENT ?if-identd
        # REMOTE_USER ?if-auth
        # REQUEST_METHOD
        env['REQUEST_METHOD'] = self.command
        #   REQUEST_URI =~=SCRIPT_NAME+PATH_INFO
        #   SCRIPT_FILENAME
        env['SCRIPT_FILENAME'] = scriptfile
        # SCRIPT_NAME
        env['SCRIPT_NAME'] = self.cgi_dir + '/' + self.cgi_script
        #   SERVER_ADDR
        #   SERVER_ADMIN
        # SERVER_NAME =header["Host"]
        env['SERVER_NAME'] = self.server.server_name
        # SERVER_PORT =int
        env['SERVER_PORT'] = str(self.server.server_port)
        # SERVER_PROTOCOL ="HTTP/1.0" e.g.
        env['SERVER_PROTOCOL'] = self.request_version
        # SERVER_SOFTWARE
        env['SERVER_SOFTWARE'] = self.version_string()
        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
            request_body = self.rfile.read(int(length))
        else:
            request_body = None
        args = [scriptfile]
        #if '=' not in decoded_query:
        #    args.append(decoded_query)
        #self.wfile.flush()
        child = subprocess.Popen(args,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 #cwd=os.path.dirname(self.cgi_script),
                                 env=env)
        out, err = child.communicate(request_body)
        rc = child.returncode
        if rc or err:
            report = 'CGI script %s returned exit code %d\n' % (self.cgi_script, rc)
            #import sys
            #print >>sys.stderr, report + err
            self.send_error(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(report)
            self.wfile.write(err)
            return
        #import sys
        #e = sys.stderr
        #print >>e, 'rc',rc,'err',repr(err),'out',repr(out)
        reply = self.MessageClass(cStringIO.StringIO(out))
        #for hdr in reply.headers:
        #    print >>e, repr(hdr)
        #for key in reply.keys():
        #    print >>e, key, reply.getheaders(key)
        status = reply.getheader('Status')
        #print >>e, 'status',repr(status)
        del reply['status']
        if status:
            self.send_response(int(status.split()[0]))
        else:
            self.send_response(200)
        # FIXME location
        body = reply.fp.read()
        #print 'body',repr(body)
        for hdr in reply.headers:
            self.wfile.write(hdr.replace('\015','').replace('\012','\015\012'))
        self.wfile.write('Content-Length: %d\015\012' % len(body))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

def test(HandlerClass = PTestCGIHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    CGIHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()
