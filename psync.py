#=======================================================================
#	$Id: psync.py,v 1.6 2011/01/31 12:39:07 pythontech Exp pythontech $
#       Another attempt at synchronisation
#
#	State
#	  .type		'd' 'f' 'l' etc.
#	  .vsn		immutable value
#	  .meta		dict with keys 'mtime' 'mode'
#	RepoState
#	  .type		'd' 'f' 'l' etc.
#	  .avsn		immutable value
#	  .bvsn		immutable value
#	  .conflict	'?' 'a' 'b' etc.
#	  .equal_a(State) -> bool
#	  .equal_b(State) -> bool
#	Collection
#	  .getstate(path) -> State
#	  .readdir(path) -> {name: State, ...}
#	  .readfile(path) -> content
#	  .readlink(path) -> link
#	  .writefile(path,content,meta) -> State
#	  .writelink(path,link) -> State
#	  .mkdir(path,meta) -> State
#	  .remove(path)
#	  .remove_recursively(path)
#	Repo
#	  .getstate(path) -> RepoState
#	  .setstate(path, type, avsn, bvsn)
#	  .delstate(path)
#	  .setconflict(path, conflict)
#	  .readdir(path) -> [name, ...]
#	  .flush()
#	  .itertree() -> iterator: (name, True|False|State)
#	Sync(Repo, Collection, Collection)
#	  .repo		Repo
#	  .a		Collection
#	  .b		Collection
#	  .run()
#	  .conflict(path, astate, bstate)
#	  .both_gone(path)
#	  .a_to_b(path, astate, bstate)
#	  .b_to_a(path, astate, bstate)
#=======================================================================
import os
import stat
import logging

class NotYet(Exception): pass
class Abstract(Exception): pass
class Conflict(Exception): pass

# Conflict modes
CF_ASK = '?'                    # Need to ask user
CF_A = 'a'                      # Changes to A win this time
CF_B = 'b'                      # Changes to B win this time
CF_ALWAYS_A = 'A'               # Changes to A always win
CF_ALWAYS_B = 'B'               # Changes to B always win

class State:
    '''
    State of an item within a collection.
      type	'f' for file, 'd' for directory,'l' for symlink
      vsn	A token, usable to detect changes unless None
      meta	dict of metadata (size, modtime, mode)
    '''
    def __init__(self, type,vsn,meta):
        self.type = type
        self.vsn = vsn
        self.meta = meta

    def __repr__(self):
        return '<State %s,%s>' % (repr(self.type), repr(self.vsn))

class RepoState:
    '''
    State of an item at last synchronisation
      type	'f' for file, 'd' for directory, 'l' for symlink
      avsn	Version token for collection A
      bvsn	Version token for collection B
      conflict	Conflict state, if any
    '''
    def __init__(self, type,avsn,bvsn,conflict=None):
        self.type = type
        self.avsn = avsn
        self.bvsn = bvsn
        self.conflict = conflict

    def __repr__(self):
        return '<RepoState %s>' % repr(self.type)

    def equal_a(self, astate):
        if astate is None:
            return False
        return (astate.type == self.type  and  astate.vsn == self.avsn)

    def equal_b(self, bstate):
        if bstate is None:
            return False
        return (bstate.type == self.type  and  bstate.vsn == self.bvsn)

class Collection:
    '''Abstract class for collection of items'''

    def getstate(self, path):
        raise Abstract

    def readdir(self, path):
        '''
        Read content of directory.  Return dict with
        key = leafname, value = state
        '''
        raise Abstract

    def readfile(self, path):
        '''Read content of regular file'''
        raise Abstract

    def readlink(self, path):
        '''Read content of symlink'''
        raise Abstract

    def writefile(self, path, content, meta):
        '''Write content of item.  Return new state'''
        raise Abstract

    def writelink(self, path, link):
        '''Write symbolic link.  Return new state'''
        raise Abstract

    def mkdir(self, path, meta):
        '''Create directory'''
        raise Abstract

    def remove(self, path):
        '''Remove file or symlink'''
        raise Abstract

    def remove_recursively(self, path):
        '''Remove item and any children, recursively'''
        state = self.getstate(path)
        if state is None:
            return
        if state.type == 'd':
            for name in self.readdir(path):
                self.remove_recursively(path+(name,))
        self.remove(path)

class DictCollection(Collection):
    '''In-memory collection'''
    def __init__(self, initial=None):
        self.root = initial or {}

    def readdir(self, path=()):
        obj = self._find(path)
        if not hasattr(obj,'items'):
            raise Exception, 'Not a directory %s' % repr(path)
        dir = {}
        for k,v in obj.items():
            dir[k] = self._getstate(v)
        return dir

    def _find(self, path):
        obj = self.root
        for step in path:
            obj = obj[step]
            # Expect KeyError if not found
        return obj

    def readfile(self, path):
        obj = self._find(path)
        if not isinstamce(obj,str):
            raise Exception, 'Not a leaf (string)'
        return obj

    def writefile(self, path, content, meta={}):
        parent = self._find(path[:-1])
        parent[path[-1]] = content
        return self._getstate(content)

    def mkdir(self, path, meta):
        parent = self._find(path[:-1])
        parent[path[-1]] = new = {}
        return self._getstate(new)

    def remove(self, path):
        parent = self._find(path[:-1])
        del parent[path[-1]]

    def getstate(self, path):
        obj = self._find(path)
        if hasattr(obj,'items'):
            return State('d',None,{})
        else:
            return State('f',obj,{})

class FileCollection(Collection):
    '''Files on local machine'''
    def __init__(self, root):
        self.root = root

    def readdir(self, path=()):
        dirname = os.path.join(self.root, *path)
        dstate = self._getstate(dirname)
        if not dstate:
            raise Exception, "No such directory %s" % repr(dirname)
        if dstate.type != 'd':
            raise Exception, "Not a directory %s" % repr(dirname)
        list = os.listdir(dirname)
        dir = {}
        for leaf in list:
            filename = os.path.join(dirname, leaf)
            #print filename
            dir[leaf] = self._getstate(filename)
        return dir

    def readfile(self, path):
        '''Read content of regular file'''
        filename = os.path.join(self.root, *path)
        fstate = self._getstate(filename)
        if not fstate:
            raise Exception, "No such file %s" % repr(filename)
        ftype = fstate.type
        if ftype != 'f':
            raise Exception, "Not a file %s" % repr(filename)
        content = open(filename).read()
        return content

    def readlink(self, path):
        '''Read content of symlink'''
        filename = os.path.join(self.root, *path)
        fstate = self._getstate(filename)
        if not fstate:
            raise Exception, "No such file %s" % repr(filename)
        ftype = fstate.type
        if ftype != 'l':
            raise Exception, "Not a symlink %s" % repr(filename)
        link = os.readlink(filename)
        return link

    def writefile(self, path, content, meta={}):
        filename = os.path.join(self.root, *path)
        newname = filename+'.psync'
        f = open(newname,'wb')
        f.write(content)
        f.close()
        # set mode, mtime
        mtime = meta.get('mtime')
        if mtime is not None:
            os.utime(newname, (mtime,mtime))
        mode = meta.get('mode')
        if mode is not None:
            os.chmod(newname, mode)
        os.rename(newname, filename)
        return self._getstate(filename)

    def writelink(self, path, link):
        filename = os.path.join(self.root, *path)
        newname = filename+'.psync'
        os.symlink(link, newname)
        os.rename(newname, filename)
        return self._getstate(filename)

    def mkdir(self, path, meta):
        dirname = os.path.join(self.root, *path)
        mode = meta.get('mode',0777) & 0777
        os.mkdir(dirname, mode)
        return self._getstate(dirname)

    def remove(self, path):
        filename = os.path.join(self.root, *path)
        try:
            st = os.lstat(filename)
        except os.error:
            return
        if os.path.isdir(filename):
            # rm -fr dir
            pass
        else:
            os.remove(filename)

    def getstate(self, path):
        filename = os.path.join(self.root, *path)
        return self._getstate(filename)

    def _getstate(self, filename):
        '''Return state object for filename, or None
        if it does not exist.
        '''
        try:
            st = os.lstat(filename)
        except os.error:
            return None
        if os.path.islink(filename):
            link = os.readlink(filename)
            return State('l',link,{})
        elif os.path.isdir(filename):
            return State('d',None,dict(mode=st.st_mode))
        elif os.path.isfile(filename):
            # Assume that contents unchanged if modtime unchanged.
            # Not necessarily true (modtime can be manually changed,
            # also if written within 1-second granularity).
            mtime = st.st_mtime
            return State('f', mtime, dict(mode=st.st_mode,
                                          size=st.st_size,
                                          mtime=mtime))
        else:
            return State('?',None,{})

class Sync:
    def __init__(self, repo, a, b):
        self.repo = repo
        self.a = a
        self.b = b
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        path = ()
        rootstate = self.repo.getstate(path)
        if not rootstate:
            astate = self.a.getstate(path)
            bstate = self.b.getstate(path)
            self.sync_initial(path, astate, bstate)
        else:
            self.sync_dir(path)

    def sync_item(self, path, astate, bstate):
        syncstate = self.repo.getstate(path)
        if syncstate:
            self.sync_update(path, astate, bstate, syncstate)
        else:
            self.sync_initial(path, astate, bstate)

    def sync_initial(self, path, astate, bstate):
        '''Perform initial synchronisation, where no shared state known'''
        spath = '/'.join(path)
        if astate and bstate:
            # Item exists in both collections
            self.logger.info('In both: %r' % spath)
            if astate.type == 'd' and bstate.type == 'd':
                self.repo.setstate(path, 'd', astate.vsn, bstate.vsn)
                self.sync_dir(path)
            else:
                self.conflict(path, astate, bstate)
        elif astate:
            self.logger.info('New in a: %r' % spath)
            self.a_to_b(path, astate, bstate)
            if astate.type == 'd':
                self.sync_dir(path)
        elif bstate:
            self.logger.info('New in b: %r' % spath)
            self.b_to_a(path, astate, bstate)
            if bstate.type == 'd':
                self.sync_dir(path)
        else:
            print 'In neither: %s' % '/'.join(path)

    def sync_update(self, path, astate, bstate, syncstate):
        '''Synchronise where previous synchronisation done'''
        if syncstate.equal_a(astate):
            # A unchanged
            if syncstate.equal_b(bstate):
                # No change
                pass
            else:
                # B changed
                self.b_to_a(path, astate, bstate)
        elif syncstate.equal_b(bstate):
            # A changed, B same
            self.a_to_b(path, astate, bstate)
        else:
            # Both changed
            if astate is None and bstate is None:
                # Both Gone
                self.both_gone(path)
            else:
                # B changed but A gone
                self.conflict(path, astate, bstate)

    def sync_dir(self, path):
        '''Synchronise directories which exist on both sides'''
        adir = self.a.readdir(path)
        bdir = self.b.readdir(path)
        sdir = self.repo.readdir(path)
        leaves = set(adir.keys() + bdir.keys() + sdir)
        self.logger.info('Leaves: %r' % leaves)
        for leaf in leaves:
            astate = adir.get(leaf)
            bstate = bdir.get(leaf)
            self.sync_item(path+(leaf,), astate, bstate)

    def conflict(self, path, astate, bstate):
        raise Conflict, 'conflict %s %s %s' % \
            (repr('/'.join(path)),repr(astate),repr(bstate))

    def both_gone(self, path):
        #raise Exception, 'Gone on both sides %s' % repr(path)
        self.repo.delstate(path)

    def a_to_b(self, path, astate, bstate):
        newstate = self.transfer(path, self.a,astate, self.b,bstate)
        if astate:
            self.repo.setstate(path, astate.type, astate.vsn, newstate.vsn)
        else:
            self.repo.delstate(path)

    def b_to_a(self, path, astate, bstate):
        newstate = self.transfer(path, self.b,bstate, self.a,astate)
        if bstate:
            self.repo.setstate(path, bstate.type, newstate.vsn, bstate.vsn)
        else:
            self.repo.delstate(path)

    def transfer(self, path, src,sstate, dest,dstate):
        newstate = None
        if dstate:
            if not sstate  or  sstate.type != dstate.type:
                dest.remove(path)
        if sstate:
            if sstate.type == 'f':
                content = src.readfile(path)
                newstate = dest.writefile(path, content, sstate.meta)
            elif sstate.type == 'l':
                link = src.readlink(path)
                newstate = dest.writelink(path, link)
            elif sstate.type == 'd':
                newstate = dest.mkdir(path, sstate.meta)
            else:
                raise Exception, 'Cannot sync type %s' % sstate.type
        return newstate

class Repo:
    '''Abstract state repository'''
    def getstate(self, path):
        '''Get RepoState for path, or None if not synced'''
        raise Abstract

    def setstate(self, path, type, avsn, bvsn):
        '''Set synchronised state'''
        raise Abstract

    def delstate(self, path):
        '''Delete path from synchronisation repository'''
        raise Abstract

    def setconflict(self, path, conflict):
        raise Abstract

    def readdir(self, path):
        '''Read items in directory'''
        raise Abstract

    def flush(self):
        '''Optional method to make changes permanent'''
        pass

    def as_data(self):
        '''Convert to dict tree with tuples (type,avsn,bvsn) as leaves.'''
        return self._as_data(self, ())

    def _as_data(self, path):
        dir = {}
        for name in self.readdir(path):
            cpath = path + (name,)
            state = self.getstate(cpath)
            if state.type=='d':
                dir[name] = self._as_data(cpath)
            else:
                dir[name] = (state.type, state.avst, state.bvsn)
        return dir

    def itertree(self):
        for x in self._itertree(self, ()):
            yield x

    def _itertree(self, path):
        for name in self.readdir(path):
            cpath = path + (name,)
            state = self._getstate(cpath)
            if state.type == 'd':
                yield name,True
                for x in self._itertree(cpath):
                    yield x
                yield name,False
            else:
                yield name,state

def repo2data(repo):
    root = {}
    stack = []
    cur = root
    for name,act in repo.itertree():
        if act is True:
            new = root[name] = {}
            stack.append(cur)
            cur = new
        elif act is False:
            cur = stack.pop()
        else:
            cur[name] = (act.type, act.avsn, act.bvsn)
    return root

class DictRepo(Repo):
    '''
    Repository of state information.
    0 is id of empty path.
    l -> last id
    i$id,$leaf -> id of child
    n$id -> leaf
    p$id -> parent id
    s$id -> (type, avsn, bvsn) at last sync
    d$id -> tuple of item ids in directory
    '''
    def __init__(self, store=None):
        if store is None:
            store = {}
        self.store = store
        self.lastid = self.store.get('l', 0)

    def _pathid(self, path, create=False):
        id = 0
        for step in path:
            sid = self.store.get('i%d,%s' % (id,step), None)
            if sid is None:
                if not create:
                    return None
                # Create new item
                self.lastid += 1
                sid = self.store['l'] = self.lastid
                self.store['i%d,%s' % (id,step)] = self.lastid
                self.store['n%d' % sid] = step
                self.store['p%d' % sid] = id
                dir = self.store.get('d%d' % id, ())
                self.store[('d%d' % id)] = dir + (sid,)
            id = sid
        return id

    def getstate(self, path):
        id = self._pathid(path)
        if id is None:
            return None
        state = self.store.get('s%d' % id, None)
        if state is None:
            return None
        conflict = self.store.get('c%d' % id, None)
        return RepoState(*(state + (conflict,)))

    def setstate(self, path, type, avsn, bvsn):
        '''Set synchronisation state'''
        id = self._pathid(path, True)
        self.store['s%d' % id] = (type, avsn, bvsn)

    def delstate(self, path):
        '''Delete synchronisation info'''
        id = self._pathid(path)
        if id is not None:
            self._del_id(id)

    def setconflict(self, path, conflict):
        id = self._pathid(path, True)
        if conflict is None:
            del self.store['c%d' % id]
        else:
            self.store['c%d' % id] = conflict

    def readdir(self, path):
        id = self._pathid(path)
        if id is None:
            return []
        cids = self.store.get('d%d' % id, ())
        return [self.store['n%d' % cid] for cid in cids]

    def as_data(self):
        return self._as_data(0)

    def _as_data(self, id):
        dir = self.store.get('d%d' % id)
        if dir is not None:
            d = {}
            for child in self.store.get('d%d' % id, ()):
                leaf = self.store.get('n%d' % child)
                obj = self._as_data(child)
                d[leaf] = obj
            return d
        else:
            return self.store.get('s%d' % id)

    def _itertree(self, id):
        cids = self.store.get('d%d' % id, ())
        for cid in cids:
            name = self.store['n%d' % cid]
            state = self.store.get('s%d' % cid, None)
            if state[0] == 'd':
                yield name,True
                for x in self._itertree(cid):
                    yield x
                yield name,False
            else:
                yield name, state
        
    def _del_id(self, id):
        '''Delete an item known to exist.'''
        # Recurse
        dir = self.store.get('d%d' % id, ())
        for child in dir:
            self._del_id(child)
        if id != 0:
            parent = self.store.get('p%d' % id, 0)
            leaf = self.store.get('n%d' % id, '')
            dir = list(self.store.get('d%d' % parent, ()))
            dir.remove(id)
            self.store['d%d' % parent] = tuple(dir)
            self._delitem('i%d,%s' % (parent,leaf))
            self._delitem('n%d' % id)
            self._delitem('p%d' % id)
        self._delitem('s%d' % id)

    def _delitem(self, key):
        try:
            del self.store[key]
        except KeyError: pass

class ShelveRepo(DictRepo):
    '''Repository using shelve for persistence in file'''
    def __init__(self, filename):
        import shelve
        d = shelve.open(filename)
        DictRepo.__init__(self, d)

    def flush(self):
        self.store.sync()

if __name__=='__main__':
    etc = FileCollection('/etc')
    print etc.readdir(('rc.d',))
    print etc.readfile(('rc.d','init.d','lvm'))
    print etc.readlink(('rc.d','rc0.d','S01halt'))
    tmp = FileCollection('/tmp')
    tmp.writefile(('chah',),'HelloWorld')
