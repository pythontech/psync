from helpers import *
import os

cgi = CgiServer(port=8183)
print 'Starting on port', cgi.port
cgi.start()
os.system('GET http://localhost:8183/htbin/t.sh')
#cgi.stop()
print 'Stopped'
print cgi.messages
