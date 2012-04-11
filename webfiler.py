#=======================================================================
#       $Id: webfiler.py,v 1.4 2011/01/31 12:41:37 pythontech Exp pythontech $
#	WebFiler as collection
#=======================================================================
from psync import Collection, State
import urllib2
import cookielib
import cStringIO
import sys

class WebFilerCollection(Collection):
    def __init__(self, url, root=(),
                 loginUrl=None, username=None, password=None):
        self.url = url
        self.root = tuple(root)
        self.loginUrl = loginUrl
        self.username = username
        self.password = password
        # User agent for HTTP requests
        self.jar = cookielib.CookieJar()
        self.agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.jar))
        self.loggedIn = False

    def readfile(self, path):
        '''Read content of regular file.'''
        if not self.loggedIn:
            self._login()
        query = {'path': self._upath(path),
                 'action': 'readfile'}
        doc = self._get(query)
        meta = doc.info()
        mime = meta.gettype()
        assert(mime == 'application/octet-stream')
        content = doc.read()
        return content

    def readlink(self, path):
        '''Read content of symlink.'''
        if not self.loggedIn:
            self._login()
        query = {'path': self._upath(path),
                 'action': 'readlink'}
        doc = self._get(query)
        meta = doc.info()
        mime = meta.gettype()
        assert(mime == 'application/x-ptwb-symlink')
        content = doc.read()
        return content

    def readdir(self, path):
        '''Read contents of directory.
        Must have already determined that it is a directory.
        '''
        if not self.loggedIn:
            self._login()
        query = {'path': self._upath(path)}
        doc = self._get(query)
        meta = doc.info()
        #print >>sys.stderr, 'mimetype',meta.gettype()
        assert(meta.gettype()=='application/x-ptwb-dir')
        dir = {}
        for line in doc:
            details = line.split()
            ctype, uleaf, mode, size, mtime = details[:5]
            if ctype=='f':
                state = State('f', int(mtime), dict(mode=int(mode,8),
                                                    size=int(size),
                                                    mtime=int(mtime)))
            elif ctype=='d':
                state = State('d', None, dict(mode=int(mode,8)))
            elif ctype=='l':
                state = State('l', ux(details[5]), {})
            else:
                state = State(ctype,None,{})
            dir[ux(uleaf)] = state
        return dir

    def writefile(self, path, content, meta={}):
        if not self.loggedIn:
            self._login()
        # FIXME only for short content...
        # Otherwise need multipart/form-data
        query = {'path': self._upath(path),
                 'action': 'write',
                 'content': cStringIO.StringIO(content)}
        if 'mtime' in meta:
            query['mtime'] = '%d' % meta['mtime']
        if 'mode' in meta:
            query['mode'] = '%o' % meta['mode']
        doc = self._upload(self.url, query)

    def mkdir(self, path, meta):
        if not self.loggedIn:
            self._login()
        query = {'path': self._upath(path),
                 'action': 'mkdir'}
        if 'mode' in meta:
            query['mode'] = '%o' % meta['mode']
        doc = self._post(self.url, query)

    def writelink(self, path, link):
        if not self.loggedIn:
            self._login()
        query = {'path': self._upath(path),
                 'action': 'writelink',
                 'link': link}
        doc = self._post(self.url, query)

    def _login(self):
        '''Log in i.e. authenticate self with server via cookie.'''
        if self.loginUrl:
            doc = self._post(self.loginUrl, {'username': self.username,
                                             'password': self.password,
                                             'login': 'Log in'})
            # Newer versions of PythonTech::Login set X-ptweb-login
            # header to indicate success or failure.
            result = doc.info().getheader('x-ptweb-login')
            if result is not None:
                if result != 'OK':
                    raise ValueError, 'Login as user %s failed' % self.username
            else:
                # Could check content
                pass
        self.loggedIn = True

    def _upath(self, path):
        return '/' + '/'.join(map(uq, self.root + path))

    def _get(self, query={}):
        '''Perform a GET request'''
        url = self.url
        if query:
            url += '?' + urlencode(query)
        #print 'query',query
        try:
            doc = self.agent.open(url)
        except urllib2.HTTPError, e:
            print >>sys.stderr, 'HTTPError %d' % e.code
            #print >>sys.stderr, e.info().fp.read()
            raise
        except urllib2.URLError, e:
            print >>sys.stderr, 'URLError %s' % e.reason
            raise
        meta = doc.info()
        #print >>sys.stderr, ''.join(meta.headers)
        #print >>sys.stderr, meta.fp.read()
        #print meta.keys()
        #print doc.__class__, doc.info().__class__
        #print 'status',doc.info()['status']
        return doc

    def _post(self, url, query={}):
        '''Perform a POST request to the given URL'''
        data = ''
        if query:
            #print 'query',query
            data = urlencode(query)
            #print 'data',data
        try:
            doc = self.agent.open(url, data)
        except urllib2.HTTPError, e:
            print 'HTTPError %d' % e.code
            raise
        except urllib2.URLError, e:
            print 'URLError %s' % e.reason
            raise
        #print doc.info()['status']
        return doc

    def _upload(self, url, query={}):
        '''Perform a POST request to the given URL'''
        content_type, data = encode_multipart_formdata(query)
        #print 'data',data
        request = urllib2.Request(url, data,
                                  {'Content-Type':content_type,
                                   'Content-Length':str(len(data))})
        try:
            doc = self.agent.open(request)
        except urllib2.HTTPError, e:
            print 'HTTPError %d' % e.code
            raise
        except urllib2.URLError, e:
            print 'URLError %s' % e.reason
            raise
        #print doc.info()['status']
        return doc

def urlencode(vars):
    return '&'.join(map(lambda kv: '='.join(map(uq, kv)),
                        vars.items()))

def uq(step):
    return urllib2.quote(step, safe='')

ux = urllib2.unquote

import random

# Pinched and modified from activestate recipe 146306...
def encode_multipart_formdata(fields):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    CRLF = '\015\012'
    parts = ['']                # To build message
    contents = []               # To check boundary
    for key, value in fields.items():
        hdrs = 'Content-Disposition: form-data; name="%s"' % str2attr(key)
        if hasattr(value,'read'):
            # Looks like an open file
            content = value.read()
            filename = getattr(value, 'name', 'unknown')
            hdrs += '; filename="%s"' % str2attr(filename) + CRLF \
                + 'Content-Type: application/octet-stream' + CRLF \
                + 'Content-Length: %d' % len(content)
        else:
            content = value
        contents.append(content)
        parts.append(hdrs + CRLF + CRLF + content + CRLF)
    BOUNDARY = None
    while BOUNDARY is None:
        #BOUNDARY = '%d' % random.randrange(0,11)
        BOUNDARY = 'wb.%09d' % random.randrange(0,1000000000)
        for c in contents:
            if BOUNDARY in c:
                #print 'boundary %s no good' % BOUNDARY
                BOUNDARY = None
                break
    #if True in [BOUNDARY in c for c in contents]
    #if filter(lambda c: BOUNDARY in c, contents)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    body = ('--' + BOUNDARY + CRLF).join(parts) \
        + '--' + BOUNDARY + '--' + CRLF
    return content_type, body

def str2attr(name):
    # FIXME should quote funny names e.g. as =?iso-8859-1?Q?Andr=E9?=
    return name

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

# For testing...
def wfc(inifile):
    ini = {}
    for line in open(inifile):
        n,v = line.rstrip('\n').split('=')
        ini[n] = v
    if 'root' in ini:
        ini['root'] = map(ux, ini['root'].split('/'))
    print 'ini',ini
    return WebFilerCollection(**ini)

