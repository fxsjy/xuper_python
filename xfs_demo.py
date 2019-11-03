#encoding=utf8
#!/bin/env python
import xuper

pysdk = xuper.XuperSDK("http://localhost:8098", "xuper")
pysdk.readkeys("./data/keys")


rsps = pysdk.invoke("simplefs2", "get", {"key":b"hello"} )
print(rsps[0][0])

rsps = pysdk.invoke("simplefs2", "put", {"key":b"/a/1.txt", "value":b"xxxxxxxxxxxxxxxxxxxxxxxxxx"} )
print(rsps[0][0])

rsps = pysdk.invoke("simplefs2", "put", {"key":b"/a/2.txt", "value":b"xxxxxxxxxxxxxxxxxxxxxxxxxx"} )
print(rsps[0][0])

rsps = pysdk.invoke("simplefs2", "scan",{"prefix":b"/a"})
print(rsps[0][0].decode())



