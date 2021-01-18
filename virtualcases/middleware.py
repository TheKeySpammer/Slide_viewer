class IFrameMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = 'frame-ancestors http://virtualacp.com http://ftmsk.uralensiswebapp.co.uk/ https://mskcc.uralensisdigital.co.uk/ https://mskcc.uralensiswebapp.co.uk/ https://demo.uralensiswebapp.co.uk/'
        return response
