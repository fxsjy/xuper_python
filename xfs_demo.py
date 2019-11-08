#encoding=utf8
#!/bin/env python
import xuper
import os, stat, errno
import os.path
import fuse
import pickle
import time
import json
from fuse import Fuse
import codecs

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0o755
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0
        self.content = b''

class Xfs(object):
    def __init__(self, xgw="http://localhost:8098", chain="xuper", contract="simplefs10"):
        self.pysdk = xuper.XuperSDK(xgw, chain)
        self.pysdk.readkeys("./data/keys")
        self.contract = contract

    def read_oldversion(self, path):
        real_path, prev_num = path.split("@")
        prev_num = int(prev_num)
        rsps = self.pysdk.preexec(self.contract, "get", {"key":real_path.encode()}) 
        rsps_obj = json.loads(rsps)
        if 'error' in rsps_obj:
            raise Exception(rsps_obj)
        obj = None
        tx_inputs_ext = rsps_obj['response']['inputs']
        for i in range(prev_num):
            obj = None
            txid = None
            for ti in tx_inputs_ext:
                if codecs.decode(ti['key'].encode(),'base64').decode() == real_path:
                    txid = ti.get('ref_txid',None)
                    break
            if txid == None:
                return None
            tx = self.pysdk.query_tx(codecs.encode(codecs.decode(txid.encode(),'base64'), 'hex').decode())
            tx_inputs_ext = tx['tx_inputs_ext']
            for to in tx['tx_outputs_ext']:
                if codecs.decode(to['key'].encode(),'base64').decode() == real_path:
                    obj = to['value']
                    break
        if obj == None:
            return None
        pobj = pickle.loads(codecs.decode(obj.encode(), 'base64'))
        return pobj

    def readobj(self, path):
        if path.find("@") != -1:
            obj = self.read_oldversion(path) 
            return obj
        rsps = self.pysdk.invoke(self.contract, "get", {"key":path.encode()} )
        buf = rsps[0][0]
        if buf == b'':
            return None
        obj = pickle.loads(buf)
        return obj

    def readall(self, path):
        obj = self.readobj(path)
        if obj == None:
            return b''
        return obj.content

    def read(self, path, offset, size):
        buf = self.readall(path)
        return  buf[offset:offset+size]

    def write(self, path, offset, data):
        if path.find('@') != -1:
            raise Exception("invalid file name:" + path)
        obj = self.readobj(path)
        buf = obj.content
        size = len(data)
        buf_len = len(buf)
        if offset > buf_len:
            buf = buf + b'\0' * (offset-buf_len)
        new_buf = buf[:offset] + data + buf[offset+size:]
        obj.content = new_buf
        obj.st_mtime = int(time.time())
        return self.pysdk.invoke(self.contract, "put", {"key":path.encode(), "value":pickle.dumps(obj)})

    def remove(self, path):
        return self.pysdk.invoke(self.contract, "put", {"key":path.encode(), "value":b'\0'})

    def truncate(self, path, size):
        st = MyStat()
        st.content = b'\0'*size
        st.st_ctime = int(time.time())
        st.st_mtime = int(time.time())
        st.st_mode = st.st_mode | stat.S_IFREG
        return self.pysdk.invoke(self.contract, "put", {"key":path.encode(), "value":pickle.dumps(st)})

    def mkdir(self, path):
        st = MyStat()
        st.content = b'\0'
        st.st_ctime = int(time.time())
        st.st_mtime = int(time.time())
        st.st_mode = st.st_mode | stat.S_IFDIR
        return self.pysdk.invoke(self.contract, "put", {"key":path.encode(), "value":pickle.dumps(st)})

    def list(self, path):
        rsps = self.pysdk.invoke(self.contract, "scan", {"prefix":path.encode()} )
        #print(rsps)
        buf = rsps[0][0]
        result = []
        for item in buf.split(b"\n"):
            child = item[len(path)+len(self.contract)+1:]
            if len(child)==0:
                continue
            if child.find(b"/") != -1:
                continue
            result.append(child.decode())
        return result



xfs = Xfs()
fuse.fuse_python_api = (0, 2)

class HelloFS(Fuse):

    def getattr(self, path):
        print("getattr", path)
        st = MyStat()
        if path == '/':
            children = xfs.list(path)
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = len(children)
        else:
            obj = xfs.readobj(path)
            if obj == None:
                return -errno.ENOENT
            if obj.st_mode & stat.S_IFREG == stat.S_IFREG:
                #print("is_file", path)
                st.st_nlink = 1
                st.st_mode = stat.S_IFREG | 0o755
            elif obj.st_mode & stat.S_IFDIR == stat.S_IFDIR:
                children = xfs.list(path)
                st.st_nlink = len(children)
                st.st_mode = stat.S_IFDIR | 0o755
            st.st_size = len(obj.content)
            st.st_ctime = obj.st_ctime
            st.st_mtime = obj.st_mtime
        return st

    def readdir(self, path, offset):
        print("readdir", path, offset)
        children = xfs.list(path)
        #print(children)
        for r in  '.', '..':
            yield fuse.Direntry(r)
        for r in children:
            yield fuse.Direntry(r)

    def create(self, path, flags, mode):
        print('create', path)
        xfs.truncate(path, 0)
        return 0

    def open(self, path, flags):
        print("open", path, flags)
        if flags & os.O_CREAT == os.O_CREAT:
            xfs.truncate(path, 0)
        return 0

    def read(self, path, size, offset):
        print("read", path, offset, size)
        buf = xfs.read(path, offset, size)
        return buf

    def write(self, path, data, offset):
        print("write", path, data, offset)
        xfs.write(path, offset, data)
        return len(data)

    def truncate(self, path, size):
        print('truncate', path, size)
        xfs.truncate(path, size)
        return 0 

    def unlink(self, path):
        print("unlink", path)
        xfs.remove(path)
        return 0

    def mkdir(self, path, mode):
        print("mkdir", path, mode)
        path = os.path.normpath(path)
        xfs.mkdir(path)
        return 0

    def rename(self, oldpath, newpath):
        print("rename", oldpath, newpath)
        data = xfs.readall(oldpath)
        xfs.truncate(newpath,0)
        xfs.write(newpath, 0, data)
        xfs.remove(oldpath)
        return 0
        

def main():
    usage="""
Userspace hello example

""" + Fuse.fusage
    server = HelloFS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()
