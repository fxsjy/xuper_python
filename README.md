# xuper_python
## usage
        import xuper
        pysdk = xuper.XuperSDK("http://localhost:8098")
        pysdk.readkeys("./data/keys")
        
        #chain_name = xuper, to = bob, amount = 88888
        pysdk.transfer("xuper", "bob", 88888)
        
        
