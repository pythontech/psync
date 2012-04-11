#=======================================================================
#	$Id: helpers.py,v 1.5 2011/02/03 13:00:46 pythontech Exp $
#       Helper functions for psync tests
#=======================================================================
import os
import sys
import shutil
from BaseHTTPServer import HTTPServer
from CGIHTTPServer import CGIHTTPRequestHandler
from ptestcgi import PTestCGIHandler
import threading

# Timestamps
T0 = 1234000000
T1 = 1234111111
T2 = 1234222222
T3 = 1234333333

# Symbolic names for some timestamps
_time2tn = {}
_tn2time = {}
for tn in ('T0','T1','T2','T3'):
    t = globals()[tn]
    _time2tn[t] = tn
    _tn2time[tn] = t

def populate(dir, **kw):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.mkdir(dir)
    dict2dir(dir, kw)

def repopulate(dir, **kw):
    dict2dir(dir, kw)

def dict2dir(dir, desc):
    for leaf,state in desc.items():
        child = os.path.join(dir,leaf)
        if isinstance(state,str):
            state = state.split(':')
        if isinstance(state, dict):
            os.mkdir(child)
            dict2dir(child, state)
        elif state[0]=='f':
            open(child,'w').write(state[1])
            if len(state) > 2:
                mtime = state[2]
                if mtime in _tn2time:
                    mtime = _tn2time[mtime]
                else:
                    mtime = int(state[2])
                os.utime(child, (mtime,mtime))
        elif state[0]=='l':
            os.symlink(state[1], child)
        else:
            raise ValueError, 'Unknown type %s' % repr(state[0])

def dir2dict(dir, long=False):
    '''Convert directory content to Python representation'''
    d = {}
    for leaf in os.listdir(dir):
        filename = os.path.join(dir, leaf)
        if os.path.islink(filename):
            d[leaf] = 'l:%s' % os.readlink(filename)
        elif os.path.isfile(filename):
            desc = 'f:' + open(filename).read()
            if long:
                st = os.lstat(filename)
                mtime = int(st.st_mtime)
                if mtime in _time2tn:
                    desc += ':'+_time2tn[mtime]
                else:
                    desc += ':%d' % mtime
            d[leaf] = desc
        elif os.path.isdir(filename):
            d[leaf] = dir2dict(filename, long)
        else:
            d[leaf] = '?'
    return d

def mtime(filename):
    '''Return modification time of file, if available'''
    try:
        st = os.lstat(filename)
        return st.st_mtime
    except os.error:
        return None

class WebFilerTest:
    '''Mixin class for running tests against webfiler collection'''
    def run(self, result=None):
        '''Override TestCase run() to run web server'''
        import unittest
        # setUpClass / tearDownClass do not appear until 2.7
        self._setUpClass()
        try:
            unittest.TestCase.run(self, result)
        finally:
            self._tearDownClass()

    def _setUpClass(self):
        self.cgi = CgiServer()
        port = self.cgi.open_port()
        #print >>sys.stderr, 'CgiServer on port %d' % port
        self.cgibase = 'http://localhost:%d/htbin/' % port

    def _tearDownClass(self):
        self.cgi.stop()

    def webfilerCollection(self):
        '''Create an instance of WebFilerCollection.
        It needs to use URLs using the server's port.
        '''
        import webfiler
        col = webfiler.WebFilerCollection(url=self.cgibase+'filer',
                                          loginUrl=self.cgibase+'login',
                                          username='psync',
                                          password='test')
        return col

class CgiServer(HTTPServer, threading.Thread):
    '''Run a web server in a separate thread for testing web-based
    collection implementations.
    '''
    def __init__(self, port=0):
        # Set environment variable for CGI scripts
        testdir = os.path.dirname(os.path.abspath(__file__))
        os.environ['PSYNC_TESTS'] = testdir
        threading.Thread.__init__(self)
        self.setName('CgiServer')
        self.setDaemon(True)
        self.messages = []
        self.ready = threading.Event() # When port opened

    def open_port(self):
        if not self.is_alive():
            self.start()
        self.ready.wait()
        return self.port

    def run(self):
        try:
            HTTPServer.__init__(self,
                                ('localhost',0),
                                CgiHandler)
            # Remember which ephemeral port used
            self.port = self.server_address[1]
            self.ready.set()
            self.serve_forever()
        except Exception, e:
            print 'CgiServer', e

    def stop(self):
        self.shutdown()
    
class CgiHandler(PTestCGIHandler):
    '''Subclass the CGI handler to log messages to an internal list
    (in the server) instead of stderr.
    '''
    def log_message(self, format, *args):
        msg = format % args
        #print '[CGI] '+msg
        self.server.messages.append(msg)

