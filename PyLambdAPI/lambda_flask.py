import json
import logging
import base64

class Response:
    def __init__(self, statusCode, body):
        self.statusCode = statusCode
        self.body = body
    def json(self):
        return {
            'statusCode': self.statusCode,
            'body': self.body
        }
    def __str__(self):
        return f"Response(statusCode={self.statusCode}, body={self.body})"
class Route:
    def __init__(self, path, http_methods=None):
        self.path = path
        self.http_methods = http_methods or ['GET']
        self.handlers = {}
        self.middleware_chain = []

    def use_middleware(self, middleware):
        if not isinstance(middleware, Middleware):
            raise ValueError("Middleware must be a subclass of Middleware")
        if not callable(middleware.process_request):
            raise ValueError("Middleware must be callable")
        self.middleware_chain.append(middleware)

    def route(self, http_method, func):
        self.handlers[http_method] = func

    def handle_request(self, method, req_params):
        for middleware in self.middleware_chain:
            req_params = middleware.process_request(req_params)
            if isinstance(req_params, Response):
                return req_params.json()
        if method in self.handlers:
            handler = self.handlers[method]
            resp = handler(req_params)
            return Response(resp.get('statusCode', 500), resp.get('body', {})).json()
        else:
            return Response(405, 'Method Not Allowed').json()

class Middleware:
    def __init__(self, **kwargs):
            self.kwargs = kwargs

    def default_process_request(self, req_params, **kwargs):
        return req_params

    def default_process_response(self, response, **kwargs):
        return response
    

class LambdaFlask:
    def __init__(self, enable_request_logging=True, enable_response_logging=True):
        self.routes = {}
        self.enable_request_logging = enable_request_logging
        self.enable_response_logging = enable_response_logging
        self.logger = logging.getLogger(__name__)

    def route(self, path, http_methods=None):
        route = Route(path, http_methods)
        self.routes[path] = route
        return route

    def process_request(self, event):
        response = Response(500, 'Unable To Process Request')
        try:
            req_path = event['requestContext']['http']['path']
            method = event['requestContext']['http']['method']
            
            req_params = self.aggregate_params(event)

            if self.enable_request_logging:
                self.log_request(method, req_path, req_params)

            if req_path in self.routes:
                route = self.routes[req_path]
                response = route.handle_request(method, req_params)
            else:
                response = Response(404, 'Route Not Found').json()
        except Exception as e:
            response = Response(500, {'error': str(e)}).json()

        if self.enable_response_logging:
            self.log_response(response)
        return Response(response.get('statusCode',500), response.get('body',{})).json()

    def execute_handler(self, handler, req_params):
        return handler(req_params)

    def aggregate_params(self, event):
        query_params = event.get('queryStringParameters', {})
        body = event.get('body', {})
        if body and event.get('isBase64Encoded', False):
            body = json.loads(base64.b64decode(body).decode('utf-8'))
        elif body:
            body = json.loads(body)
        params = {**query_params, **body}
        params['headers']=event['headers']
        return params

    def log_request(self, method, path, params):
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info("Request - Method: %s, Path: %s, Params: %s", method, path, params)

    def log_response(self, response):
        if self.logger.isEnabledFor(logging.INFO):
            statusCode,body=response.get('statusCode',500), response.get('body','No Body Recieved in Response')
            self.logger.info("Response - Status Code: %s, Body: %s", statusCode,body)

    def route_decorator(self, path, http_methods=None, middlewares=None, **middleware_kwargs):
        if middlewares is None:
            middlewares = []

        def decorator(func):
            route = self.route(path, http_methods)
            for middleware in middlewares:
                print("here")
                route.use_middleware(middleware)
            route.route(http_methods[0], func)
            return func

        return decorator
