#encoding=utf8
#!/bin/env python
import time
import json
import requests
import ecdsa
from ecdsa.util import sigencode_der, sigdecode_der
import base64
import hashlib
import binascii
from pprint import pprint
from ecdsa import ellipticcurve, NIST256p, SigningKey, VerifyingKey

TxTemplate = '''
{   "txid":"",
    "tx_inputs": [
    ],
    "tx_outputs": [
    ],
    "desc": "",
    "nonce": "",
    "timestamp": "",
    "version": 1,
    "tx_inputs_ext":[
    ],
    "tx_outputs_ext":[
    ],
    "initiator": "",
    "auth_require": [
    ],
    "initiator_signs": [
    ],
    "auth_require_signs": [
    ]
}
'''

ResTypeEnum = {
	"CPU":0,
  	"MEMORY":1,
  	"DISK":2,
  	"XFEE":3
}

def double_sha256(data):
	s1 = hashlib.sha256(data).digest()
	return hashlib.sha256(s1)

def go_style_dumps(data):
	return json.dumps(data,separators=(',',':'),sort_keys=False)
	
class XuperSDK(object):
	def __init__(self, url, bcname):
		self.url = url
		self.bcname = bcname

	def __encodeTx(self, tx, include_sign = False):
		s = ""
		for tx_input in tx['tx_inputs']:
			s += go_style_dumps(tx_input['ref_txid'])	
			s += "\n"
			s += go_style_dumps(tx_input['ref_offset'])
			s += "\n"
			s += go_style_dumps(tx_input['from_addr'])
			s += "\n"
			s += go_style_dumps(tx_input['amount'])
			s += "\n"
			s += go_style_dumps(tx_input.get("frozen_height",0))
			s += "\n"
		s += go_style_dumps(tx['tx_outputs'])
		s += "\n"
		if len(tx['desc']) > 0:
			s += go_style_dumps(tx['desc'])
			s += "\n"
		s += go_style_dumps(tx['nonce'])
		s += "\n"
		s += go_style_dumps(tx['timestamp'])
		s += "\n"
		s += go_style_dumps(tx['version'])
		s += "\n"
		for tx_input_ext in tx['tx_inputs_ext']:
			s += go_style_dumps(tx_input_ext['bucket'])
			s += "\n"
			s += go_style_dumps(tx_input_ext['key'])
			s += "\n"
			s += go_style_dumps(tx_input_ext['ref_txid'])
			s += "\n"
			s += go_style_dumps(tx_input_ext.get('ref_offset',0))
			s += "\n"
		for tx_output_ext in tx['tx_outputs_ext']:
			s += go_style_dumps(tx_output_ext['bucket'])
			s += "\n"
			s += go_style_dumps(tx_output_ext['key'])
			s += "\n"
			s += go_style_dumps(tx_output_ext['value'])
			s += "\n"
		if 'contract_requests' not in tx:
			s += "null"  # contract request
			s += "\n"
		else:
			s += go_style_dumps(tx['contract_requests'])
			s += "\n"
		s += go_style_dumps(tx['initiator'])
		s += "\n"
		s += go_style_dumps(tx['auth_require'])
		s += "\n"
		if include_sign:
			s += go_style_dumps(tx['initiator_signs'])	
			s += "\n"
			s += go_style_dumps(tx['auth_require_signs'])
			s += "\n"	
		s += "false\n" #coinbase
		s += "false\n" #autogen	
		return s.encode()

	def __make_txid(self, tx):
		json_multi = self.__encodeTx(tx, True)
		#print(json_multi.decode())
		return double_sha256(json_multi)

	def sign_tx(self, tx):
		raw = self.__encodeTx(tx, False)
		#print(raw.decode())
		s = self.private_key.sign(raw, hashfunc=double_sha256, sigencode=sigencode_der)
		tx['auth_require_signs'][0]['Sign'] = base64.b64encode(s).decode()
		tx['initiator_signs'][0]['Sign'] = base64.b64encode(s).decode()
		txid = self.__make_txid(tx).digest()
		tx['txid'] = base64.b64encode(txid).decode()
	
	def readkeys(self, path):
		self.address = open(path + "/address").read()
		self.private_key_js = open(path + "/private.key").read()
		self.public_key_js = open(path + "/public.key").read()
		sk_obj = json.loads(self.private_key_js)
		X = int(sk_obj['X'])
		Y = int(sk_obj['Y'])
		D = int(sk_obj['D'])
		self.public_key = VerifyingKey.from_public_point(ellipticcurve.Point(NIST256p.curve, X, Y), NIST256p, double_sha256)
		self.private_key = SigningKey.from_secret_exponent(D, NIST256p, double_sha256)
		#print(self.private_key.privkey.public_key.point.x())
		#print(self.private_key.privkey.public_key.point.y())

	def post_tx(self, tx):
		payload = {
			'bcname':self.bcname,
			'header':{'logid':'pysdk_post_tx'+str(int(time.time()*1e6)) },
			'txid': tx['txid'],
			'tx': tx
		}	
		#print(json.dumps(payload))
		return requests.post(self.url + "/v1/post_tx", data = json.dumps(payload)).content

	def preexec(self, contract, method, args, module="wasm"):
		payload = {
			'bcname':self.bcname,
			'header':{'logid':'pysdk_preexec'+str(int(time.time())*1e6)},
			'requests':[
				{
					'module_name': module,
					'contract_name': contract,
					'method_name':method,
					'args':dict([(k,base64.b64encode(v).decode()) for k,v in args.items()]),
				}
			],
			'initiator':self.address,
			'auth_require':[self.address]
		}
		#print(json.dumps(payload))
		return requests.post(self.url + "/v1/preexec", data = json.dumps(payload)).content

	def invoke(self, contract, method, args, module="wasm"):
		rsps = self.preexec(contract, method, args, module)
		preexec_result = json.loads(rsps)
		contract_info = {}
		contract_info['tx_inputs_ext'] = preexec_result['response']['inputs']
		contract_info['tx_outputs_ext'] = preexec_result['response']['outputs']
		contract_info['contract_requests'] = preexec_result['response']['requests']
		contract_requests = contract_info["contract_requests"]
		for req in contract_requests:
			for res_limit in req['resource_limits']:
				if 'type' in res_limit:
					res_limit['type'] = ResTypeEnum[res_limit['type']]
				if 'limit' in res_limit:
					res_limit['limit'] = int(res_limit['limit'])
		return_msg = preexec_result['response']['response']
		fee = preexec_result['response']['gas_used']
		self.transfer('$', int(fee)+10, '', contract_info)
		return [base64.b64decode(x) for x in return_msg], int(fee)

	def transfer(self, to_address, amount, desc='', contract_info = None):
		payload = {
			'bcname':self.bcname,
			'address': self.address,
			'totalNeed': str(amount),
			'header':{'logid':'pysdk_'+str(int(time.time()*1e6)) },
			'needLock': False
		}	
		select_response = requests.post(self.url + "/v1/select_utxos_v2", data = json.dumps(payload))
		selected_obj = json.loads(select_response.content)	
		tx = json.loads(TxTemplate)
		#pprint(selected_obj)
		tx['tx_inputs'] = selected_obj['utxoList']
		for x in tx['tx_inputs']:
			x['ref_txid'] = x['refTxid']
			x['ref_offset'] = x.get('refOffset', 0)
			x['from_addr'] = base64.b64encode(self.address.encode()).decode()
			del x['refTxid']
			del x['toAddr']
			if 'refOffset' in x:
				del x['refOffset']
		total_selected = int(selected_obj['totalSelected'])
		output_return = total_selected - amount
		tx['tx_outputs'].append(
			{
				'amount':base64.b64encode(amount.to_bytes(byteorder='big',length=32).lstrip(b'\0')).decode(),
				'to_addr': base64.b64encode(to_address.encode('ascii')).decode()
			}
		)
		tx['tx_outputs'].append(
			{
				'amount':base64.b64encode(output_return.to_bytes(byteorder='big',length=32).lstrip(b'\0')).decode(),
				'to_addr': base64.b64encode(self.address.encode()).decode()
			}
		)
		tx['desc'] = base64.b64encode(desc.encode()).decode()
		tx['nonce'] = str(int(time.time()*1e6)) 
		tx['timestamp'] = int(time.time()*1e6)
		tx['initiator'] = self.address
		tx['auth_require'].append(self.address)
		tx['initiator_signs'].append({
			'PublicKey':self.public_key_js,
			'Sign':''
		})
		tx['auth_require_signs'].append({
			'PublicKey':self.public_key_js,
			'Sign':''
		})
		if contract_info != None:
			tx.update(contract_info)
		self.sign_tx(tx)
		#print(json.dumps(tx))
		res = self.post_tx(tx)
		print("txid:", binascii.hexlify(base64.b64decode(tx['txid'])).decode())
		
		

if __name__ == "__main__":
	pysdk = XuperSDK("http://localhost:8098", "xuper")
	pysdk.readkeys("./data/keys")

	pysdk.transfer("bob", 88888, desc="hello world")
	#resps = pysdk.preexec("counter", "increase", {"key":b"counter"})
	#print(resps.decode())
	rsps = pysdk.invoke("counter", "increase", {"key":b"counter"})
	print("response & fee", rsps)

