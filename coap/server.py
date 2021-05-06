from coapthon.resources.resource import Resource
from coapthon.server.coap import CoAP
from coapthon import defines
import json
import requests

# http_api_url = 'http://146.193.41.162:9000/api/reading'
http_api_url = "http://7903d0bd85ec.ngrok.io/api/reading"

class LysResource(Resource):
    def __init__(self, name="LysResource", coap_server=None):
        super(LysResource, self).__init__(name, coap_server, visible=False,
                                            observable=False, allow_children=False)
        self.payload = "Basic Resource"
        self.resource_type = "rt1"
        self.content_type = "text/plain"
        self.interface_type = "if1"

    def render_GET_advanced(self, request, response):
        response.content_type = defines.Content_types["application/json"]
        response.payload = '{"msg":"hello"}'

        return self, response

    def render_PUT_advanced(self, request, response):
        # self.edit_resource(request)
        response.content_type = defines.Content_types["application/json"]

        try:
            json.loads(request.payload)
        except:
            response.payload = json.dumps({"error":"wrong format"})
            return self, response

        try:
            resp = requests.post(http_api_url, json = {'data':request.payload}, headers={'Authorization':'Bearer 123'}, timeout=10)
        except Exception:
            response.content_type = defines.Content_types["application/json"]
            response.payload = json.dumps({"error":"failed to proxy request"})
            return self, response

        response.payload = json.dumps(resp.json())

        return self, response

    def render_POST(self, request):
        res = self.init_resource(request, LysResource())
        return res

    def render_DELETE(self, request):
        return True

class CoAPServer(CoAP):
    def __init__(self, host, port, multicast=False):
        CoAP.__init__(self,(host,port),multicast)
        self.add_resource('lys/',LysResource())
        # self.add_resource('/',LysResource())
        print(f"CoAP server started on {str(host)}:{str(port)}")
        # print(self.root.dump())

def main():
    ip = "0.0.0.0"
    port = 5683
    multicast=False
    server = CoAPServer(ip,port,multicast)
    try:
        server.listen(10)
    except KeyboardInterrupt:
        server.close()

if __name__=="__main__":
    main()