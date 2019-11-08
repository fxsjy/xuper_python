#encoding=utf8
#!/bin/env python
import xuper

pysdk = xuper.XuperSDK("http://localhost:8098", "xuper")
pysdk.readkeys("./data/keys")


account_name = "XC1111111111111111@xuper"
pysdk.transfer(account_name, 10000000, desc="start funds")
pysdk.set_account(account_name)
rsps = pysdk.deploy(account_name, 'simplefs10', open('./data/wasm/simplefs.wasm','rb').read(), {})
print(rsps)


