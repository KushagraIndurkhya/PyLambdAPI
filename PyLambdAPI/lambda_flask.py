import json
import logging
import base64
ALLOWED_SOURCES = ['function_url', 'api_gateway_proxy']


class swagger_generator:
    def __init__(self, app, title, version, description):
        self.app = app
        self.title = title
        self.version = version
        self.description = description
        self.swagger = {
            "swagger": "2.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description
            },
            "schemes": [
                "https"
            ],
            "paths": {},
            "definitions": {}
        }
        self.paths = self.swagger['paths']
        self.definitions = self.swagger['definitions']

    def build_swagger_parameters(self, params_dict):
        parameters = []
        for param_name, param_type in params_dict.items():
            if isinstance(param_type, dict):
                # Handle nested parameters
                nested_parameters = self.build_swagger_parameters(param_type)
                parameters.extend(nested_parameters)
            else:
                print(
                    param_type.__str__
                )
                # Handle non-nested parameters
                parameters.append({
                    'name': param_name,
                    'in': 'query',
                    'required': True,
                    'description': '',
                    'type': param_type.__name__,
                })
        return parameters

    def generate_method_schema(self, method, path, handler):
        schema = {
            "tags": [
                path
            ],
            "summary": handler.func.__doc__,
            "consumes": [
                "application/json"
            ],
            "produces": [
                "application/json"
            ],
            "parameters": [],
            "responses": {
                "200": {
                    "description": "Successful Operation"
                }
            }
        }
        if handler.func.__annotations__:
            for param in handler.func.__annotations__:
                if param == 'return':
                    schema['responses']['200']['schema'] = {
                        "$ref": "#/definitions/" + param
                    }
                elif param == 'req_params':
                    schema['parameters'] = self.build_swagger_parameters(
                        handler.func.__annotations__[param])
        return schema

    def add_route(self, path):
        if path in self.app.routes and path not in self.paths:
            route = self.app.routes[path]
            self.paths[path] = {}
            for method in route.methods:
                self.paths[path][method.lower()] = self.generate_method_schema(
                    method, path, route.methods[method])

    def generate(self):
        for path in self.app.routes:
            self.add_route(path)
        return self.swagger


class Response:
    def __init__(self, statusCode, body, headers=None, isBase64Encoded=False, isApiGatewayEvent=False):
        self.statusCode = statusCode
        self.body = body
        self.body_encoded = isBase64Encoded
        self.headers = headers
        self.isApiGatewayEvent = isApiGatewayEvent

    def json(self):
        if self.isApiGatewayEvent:
            return {
                'statusCode': self.statusCode,
                'body': self.body if isinstance(self.body, str) else json.dumps(self.body)
            }
        else:
            return {
                'statusCode': self.statusCode,
                'body': self.body
            }

    def __str__(self):
        return f"Response(statusCode={self.statusCode}, body={self.body})"


class MethodHandler:
    def __init__(self, func):
        self.func = func
        self.middlewares = []

    def use_middleware(self, middleware):
        if not isinstance(middleware, Middleware):
            raise ValueError("Middleware must be a subclass of Middleware")
        if not callable(middleware.process_request):
            raise ValueError("Middleware must be callable")
        self.middlewares.append(middleware)

    def execute(self, req_params):
        for middleware in self.middlewares:
            req_params = middleware.process_request(req_params)
            if isinstance(req_params, Response):
                return req_params.json()
        return self.func(req_params)


class Route:
    def __init__(self, path, http_methods=None):
        self.path = path
        # Update Route to capture path parameters denoted with `{param}`
        self.param_keys = [part[1:-1] for part in path.split("/")
                           if part.startswith("{") and part.endswith("}")]
        self.http_methods = http_methods or ['GET']
        self.methods = {}  # Dictionary to store registered methods

    def route(self, http_method, func):
        self.methods[http_method] = MethodHandler(func)

    def use_middleware(self, http_method, middleware):
        if http_method not in self.methods:
            raise ValueError(f"No method registered for {http_method}")
        self.methods[http_method].use_middleware(middleware)

    def handle_request(self, method, req_params):
        if method in self.methods:
            return self.methods[method].execute(req_params)
        else:
            return Response(405, 'Method Not Allowed').json()


class Middleware:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def default_process_request(self, req_params, **kwargs):
        return req_params

    def default_process_response(self, response, **kwargs):
        return response


class RequestInfo:
    def _aggregate_params(self, path, route_path,
                          query_string_params,
                          body, headers, is_base64_encoded):

        # Parse path parameters
        param_values = [
            part for path_part, route_part in
            zip(path.split("/"), route_part.split("/"))
            if route_part.startswith("{") and endswith("}")
        ]
        path_params = dict(zip(route.param_keys, param_values))
        params = {**path_params, **query_string_params, **body}

        if body and is_base64_encoded:
            body = {
                'base64': True,
                'file': base64.b64decode(body)
            }
        elif body:
            body = json.loads(body) if body else {}
        params = {**query_string_params, **body}
        params['headers'] = headers
        return params

    def __init__(self, path, route_path, http_method, query_string_params, body, headers, is_base64_encoded, aggregate=True, identity=None):
        self.path = path
        self.req_params = self._aggregate_params(
            path, route_path, query_string_params,
            body, headers, is_base64_encoded)
        self.http_method = http_method
        if aggregate:
            self.req_params = self._aggregate_params(
                query_string_params, body, headers, is_base64_encoded)
        else:
            self.req_params = {
                'queryStringParameters': query_string_params,
                'body': body,
                'headers': headers,
                'isBase64Encoded': is_base64_encoded
            }
        self.identity = identity

    def log(self, logger):
        if logger.isEnabledFor(logging.INFO):
            logger.info("Request - Method: %s, Path: %s, Params: %s",
                        self.http_method, self.path, self.req_params)

    def route(self):
        return self.path

    def method(self):
        return self.http_method

    def params(self):
        return self.req_params


class utills:

    def _process_function_url_event(self, event):
        path = event['requestContext']['http']['path']
        method = event['requestContext']['http']['method']
        query_params = event.get('queryStringParameters', {})
        body = event.get('body', {})
        isBase64Encoded = event.get('isBase64Encoded', False)
        headers = event.get('headers', {})
        return RequestInfo(path=path, http_method=method, query_string_params=query_params, body=body, headers=headers, is_base64_encoded=isBase64Encoded)

    def _process_api_url_event(self, event):
        path = event['path']
        method = event['httpMethod']
        query_params = event.get('queryStringParameters', {})
        body = event.get('body', {})
        isBase64Encoded = event.get('isBase64Encoded', False)
        headers = event.get('headers', {})
        identity = event.get('requestContext', {}).get('identity', {})
        return RequestInfo(path=path, http_method=method, query_string_params=query_params, body=body, headers=headers, is_base64_encoded=isBase64Encoded, aggregate=True, identity=identity)

    def process_event(self, event, type):
        if type == 'function_url':
            return self._process_function_url_event(event)
        elif type == 'api_gateway_proxy':
            return self._process_api_url_event(event)
        else:
            raise ValueError("Invalid Type")


class LambdaFlask:
    def __init__(self, source='function_url', enable_request_logging=True, enable_response_logging=True):
        self.routes = {}
        self.enable_request_logging = enable_request_logging
        self.enable_response_logging = enable_response_logging
        self.source = source
        self.isApiGatewayEvent = False
        if source not in ALLOWED_SOURCES:
            raise ValueError("Source Not Allowed")
        if source == 'api_gateway_proxy':
            self.isApiGatewayEvent = True
        self.logger = logging.getLogger(__name__)

    def route(self, path, http_methods=None):
        if path in self.routes:
            route = self.routes[path]
        else:
            route = Route(path, http_methods)
            self.routes[path] = route
        return route

    def match_route(self, request_path):
        for route_path in self.routes:
            if (len(request_path.split("/")) ==
                    len(route_path.split("/"))):
                matched = all(
                    rp == pp or (rp.startswith("{") and rp.endswith("}"))
                    for rp, pp in zip(route_path.split("/"),
                                      request_path.split("/")))
                if matched:
                    return self.routes[route_path]
                return None

    def process_request(self, event):
        response = Response(500, 'Unable To Process Request',
                            isApiGatewayEvent=self.isApiGatewayEvent)
        try:
            req_info = utills().process_event(event, self.source)
            matched_route = self.match_route(req_info.route())
            if matched_route:
                response = matched_route.handle_request(
                    req_info.method(), req_info.params())
            else:
                response = Response(
                    404, 'Route Not Found', isApiGatewayEvent=self.isApiGatewayEvent).json()

            if self.enable_request_logging:
                req_info.log(self.logger)

        except Exception as e:
            response = Response(
                500, {'error': str(e)}, isApiGatewayEvent=self.isApiGatewayEvent).json()

        if self.enable_response_logging:
            self.log_response(response)
        return Response(response.get('statusCode', 500), response.get('body', {}), response.get('headers', {}), response.get('isBase64Encoded', False), self.isApiGatewayEvent).json()

    def execute_handler(self, handler, req_params):
        return handler(req_params)

    def get_registered_routes(self):
        return self.routes

    def log_response(self, response):
        if self.logger.isEnabledFor(logging.INFO):
            statusCode, body = response.get('statusCode', 500), response.get(
                'body', 'No Body Recieved in Response')
            self.logger.info(
                "Response - Status Code: %s, Body: %s", statusCode, body)

    def route_decorator(self, path, http_methods=None, middlewares=None, **middleware_kwargs):
        if middlewares is None:
            middlewares = []

        def decorator(func):
            route = self.route(path, http_methods)
            for http_method in http_methods:
                route.route(http_method, func)
                for middleware in middlewares:
                    route.use_middleware(http_method, middleware)
            return func

        return decorator
