#=======================================================================
#       $Id$
#	Batch synchroniser
#=======================================================================
import psync
import sys

class BatchSync(psync.Sync):
    def conflict(self, path, state, bstate):
        print 'Conflict %s' % ('/'.join(path))
        self.repo.setconflict(path, psync.CF_ASK)

