import xuper
import time

pysdk = xuper.XuperSDK("http://localhost:8098", "xuper")
pysdk.readkeys("./data/keys")

#1. normal token transfer
pysdk.transfer("bob", 88888, desc="hello world")

#2. pre-execute contract
rsps = pysdk.preexec("counter", "get", {"key":b"counter"})
print(rsps.decode())


#3. call contract 
rsps = pysdk.invoke("counter", "increase", {"key":b"counter"})
print(rsps)

#4. create a new account 
new_account_name = pysdk.new_account()
print("wait acl confirmed....")
time.sleep(3)


#5. deploy contract
pysdk.transfer(new_account_name, 10000000, desc="start funds")
pysdk.set_account(new_account_name)
rsps = pysdk.deploy(new_account_name, 'counter100', open('/tmp/counter.wasm','rb').read(), {'creator':b'sjy'})
print(rsps)

