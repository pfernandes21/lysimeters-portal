from coapthon.client.helperclient import HelperClient
from coapthon.messages.request import Request
from coapthon import defines
import sys
#host = "146.193.41.162"
host = "85.246.38.211"
port = 5683
path = "lys/"
payload = 'text/plain'

client = HelperClient(server=(host, port))

try:
	request = Request()
	request.code = defines.Codes.PUT.number
	request.type = defines.Types['NON']
	request.destination = (host, port)
	request.uri_path = path
	request.content_type = defines.Content_types["application/json"]
	#request.payload = '{"id": 1, "humidity20": 20.12, "humidity40": 20.22, "humidity60": 20.32, "pressure": 20.42, "init":"true"}'
	request.payload = sys.argv[1]
	response = client.send_request(request)
	print(response.payload)
	client.stop()
except KeyboardInterrupt:
	client.stop()