# xuper_python
## depends
        Python Version:  only python3 
        pip install ecdsa
        pip install requests
## start server
        nohup ./xchain &
        nohup ./xchain-httpgw &
## usage
        import xuper
        pysdk = xuper.XuperSDK("http://localhost:8098")
        pysdk.readkeys("./data/keys")
        
        #chain_name = xuper, to = bob, amount = 88888
        pysdk.transfer("xuper", "bob", 88888, desc="hello wolrd")
        
        
