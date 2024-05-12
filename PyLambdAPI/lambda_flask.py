import json
import logging
import base64
ALLOWED_SOURCES = ['function_url', 'api_gateway_proxy']


class swagger_generator:
    """
    This class is responsible for generating Swagger (OpenAPI) documentation
    for a web application dynamically based on the configured routes and handlers.
    """
    def __init__(self, app, title, version, description):
        """
        Initializes a new instance of the SwaggerGenerator with basic configuration.

        :param app: Reference to the main application or framework instance.
        :param title: Title of the API for Swagger documentation.
        :param version: Version of the API for Swagger documentation.
        :param description: Description of the API for Swagger documentation.
        """
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
    def build_swagger_parameters(self,params_dict):
        """
        Constructs the Swagger parameters for API documentation from a dictionary of parameter specifications.

        :param params_dict: A dictionary where keys are parameter names and values are their types or nested parameter dictionaries.
        :return: A list of Swagger-compatible parameter dictionaries.
        """
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
        """
        Generates the Swagger schema for a specific API method.

        :param method: HTTP method (GET, POST, etc.).
        :param path: URL path for the API method.
        :param handler: The handler function for the API method.
        :return: A dictionary representing the Swagger schema of the method.
        """
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
                    schema['parameters'] = self.build_swagger_parameters(handler.func.__annotations__[param])
        return schema

    def add_route(self, path):
        """
        Adds a route to the Swagger documentation if it's not already present.

        :param path: URL path of the route.
        """
        if path in self.app.routes and path not in self.paths:
            route = self.app.routes[path]
            self.paths[path] = {}
            for method in route.methods:
                self.paths[path][method.lower()] = self.generate_method_schema(
                    method, path, route.methods[method])

    def generate(self):
        """
        Generates the complete Swagger documentation by iterating over all configured routes.

        :return: The full Swagger documentation as a dictionary.
        """
        for path in self.app.routes:
            self.add_route(path)
        return self.swagger


class Response:
    """
    Represents a response object for API calls, encapsulating status code, body, and headers.
    """
    def __init__(self, statusCode, body, headers=None, isBase64Encoded=False, isApiGatewayEvent=False):
        """
        Initializes a new instance of the Response class.

        :param statusCode: HTTP status code of the response.
        :param body: Content of the response.
        :param headers: Optional HTTP headers for the response.
        :param isBase64Encoded: Flag indicating if the response body is base64-encoded.
        :param isApiGatewayEvent: Flag indicating if the response is for an API Gateway event.
        """
        self.statusCode = statusCode
        self.body = body
        self.body_encoded = isBase64Encoded
        self.headers = headers
        self.isApiGatewayEvent = isApiGatewayEvent

    def json(self):
        """
        Converts the response object to a JSON format suitable for API responses.

        :return: A dictionary representing the JSON-formatted response.
        """
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
    """
    Manages the execution of a specific API method, including any middleware processing that needs to occur before the method is called.
    """
    def __init__(self, func):
        """
        Initialize the handler with a specific function.

        :param func: The API function to handle.
        """
        self.func = func
        self.middlewares = []

    def use_middleware(self, middleware):
        """
        Adds middleware to be executed before the API function.

        :param middleware: A middleware instance that must have a callable 'process_request' method.
        :raises ValueError: If middleware is not an instance of Middleware or its 'process_request' method is not callable.
        """
        if not isinstance(middleware, Middleware):
            raise ValueError("Middleware must be a subclass of Middleware")
        if not callable(middleware.process_request):
            raise ValueError("Middleware must be callable")
        self.middlewares.append(middleware)

    def execute(self, req_params):
        """
        Executes all middleware in order and then the API function.

        :param req_params: The request parameters passed to the middlewares and the API function.
        :return: The result of the API function or a middleware-generated response.
        """
        for middleware in self.middlewares:
            req_params = middleware.process_request(req_params)
            if isinstance(req_params, Response):
                return req_params.json()
        return self.func(req_params)


class Route:
    """
    Represents a route in the API, managing different methods and their handlers.
    """
    def __init__(self, path, http_methods=None):
        """
        Initializes a route with a specified path and optionally specified HTTP methods.

        :param path: The URL path for this route.
        :param http_methods: Optional list of HTTP methods to support. Defaults to ['GET'] if not specified.
        """
        self.path = path
        self.http_methods = http_methods or ['GET']
        self.methods = {}  # Dictionary to store registered methods

    def route(self, http_method, func):
        """
        Registers a function to a HTTP method for this route.

        :param http_method: The HTTP method (e.g., 'GET', 'POST').
        :param func: The function to handle requests for the specified method.
        """
        self.methods[http_method] = MethodHandler(func)

    def use_middleware(self, http_method, middleware):
        """
        Attaches a middleware to a specific HTTP method for this route.

        :param http_method: The HTTP method to attach the middleware to.
        :param middleware: The middleware instance to attach.
        :raises ValueError: If no method is registered under http_method.
        """
        if http_method not in self.methods:
            raise ValueError(f"No method registered for {http_method}")
        self.methods[http_method].use_middleware(middleware)

    def handle_request(self, method, req_params):
        """
        Handles a request by executing the corresponding method handler.

        :param method: The HTTP method of the request.
        :param req_params: The parameters of the request.
        :return: The response from the handler or a 405 Method Not Allowed response if the method is not supported.
        """
        if method in self.methods:
            return self.methods[method].execute(req_params)
        else:
            return Response(405, 'Method Not Allowed').json()


class Middleware:
    """
    Base class for creating middleware that can intercept and modify requests and responses.
    """
    def __init__(self, **kwargs):
        """
        Initializes middleware with optional keyword arguments.

        :param kwargs: Keyword arguments specific to middleware logic.
        """
        self.kwargs = kwargs

    def default_process_request(self, req_params, **kwargs):
        """
        Default request processing method. Can be overridden by subclasses.

        :param req_params: The original request parameters.
        :param kwargs: Optional keyword arguments.
        :return: Modified or unmodified request parameters.
        """
        return req_params

    def default_process_response(self, response, **kwargs):
        """
        Default response processing method. Can be overridden by subclasses.

        :param response: The response to process.
        :param kwargs: Optional keyword arguments.
        :return: Modified or unmodified response.
        """
        return response


class RequestInfo:
    """
    Encapsulates details of an HTTP request, aggregating query string, body, headers, and other parameters.
    """
    def _aggregate_params(self, query_string_params, body, headers, is_base64_encoded):
        """
        Aggregates and possibly decodes parameters from different parts of the request.

        :param query_string_params: Query string parameters.
        :param body: Body of the request, potentially in JSON or base64 encoded.
        :param headers: HTTP headers of the request.
        :param is_base64_encoded: Flag indicating whether the body is base64 encoded.
        :return: A dictionary containing all parameters.
        """
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

    def __init__(self, path, http_method, query_string_params, body, headers, is_base64_encoded, aggregate=True, identity=None):
        """
        Initializes a RequestInfo object with details about the request.

        :param path: URL path of the request.
        :param http_method: HTTP method used.
        :param query_string_params: Query parameters included in the URL.
        :param body: Body of the request.
        :param headers: HTTP headers.
        :param is_base64_encoded: Indicates if the body is base64 encoded.
        :param aggregate: Whether to aggregate all parameters into a single attribute.
        :param identity: Optional identity information (e.g., from a user session).
        """
        self.path = path
        self.http_method = http_method
        if aggregate:
            self.req_params = self._aggregate_params(query_string_params, body, headers, is_base64_encoded)
        else:
            self.req_params = {
                'queryStringParameters': query_string_params,
                'body': body,
                'headers': headers,
                'isBase64Encoded': is_base64_encoded
            }
        self.identity = identity

    def log(self, logger):
        """
        Logs request details using a provided logger.

        :param logger: Logger to use for logging the request details.
        """
        if logger.isEnabledFor(logging.INFO):
            logger.info("Request - Method: %s, Path: %s, Params: %s",
                        self.http_method, self.path, self.req_params)

    def route(self):
        """
        Returns the path associated with this request.

        :return: URL path as a string.
        """
        return self.path

    def method(self):
        """
        Returns the HTTP method used for this request.

        :return: HTTP method as a string.
        """
        return self.http_method

    def params(self):
        """
        Returns the aggregated or individual parameters of the request.

        :return: Dictionary of parameters.
        """
        return self.req_params


class utills:
    """
    Provides utility functions to process events received by a Lambda function from AWS API Gateway.
    """
    def _process_function_url_event(self, event):
        """
        Processes events triggered by direct URL access in AWS Lambda.

        :param event: Event data received from AWS Lambda.
        :return: A RequestInfo object containing the details of the request.
        """
        path = event['requestContext']['http']['path']
        method = event['requestContext']['http']['method']
        query_params = event.get('queryStringParameters', {})
        body = event.get('body', {})
        isBase64Encoded = event.get('isBase64Encoded', False)
        headers = event.get('headers', {})
        return RequestInfo(path=path, http_method=method, query_string_params=query_params, body=body, headers=headers, is_base64_encoded=isBase64Encoded)

    def _process_api_url_event(self, event):
        """
        Processes API Gateway proxy events, handling more complex scenarios like different methods and authentication.

        :param event: Event data from API Gateway.
        :return: A RequestInfo object containing the details of the request.
        """
        path = event['path']
        method = event['httpMethod']
        query_params = event.get('queryStringParameters') if event.get(
            'queryStringParameters', None) else {}
        body = event.get('body') if event.get('body', None) else {}
        isBase64Encoded = event.get('isBase64Encoded', False)
        headers = event.get('headers', {})
        identity = event.get('requestContext', {}).get('identity', {})
        return RequestInfo(path=path, http_method=method, query_string_params=query_params, body=body, headers=headers, is_base64_encoded=isBase64Encoded, aggregate=True, identity=identity)

    def process_event(self, event, type):
        """
        Determines the type of event (function URL or API Gateway proxy) and processes it accordingly.

        :param event: Event data received from AWS Lambda.
        :param type: Type of the event to process ('function_url' or 'api_gateway_proxy').
        :return: A RequestInfo object containing the details of the request.
        :raises ValueError: If the event type is not recognized.
        """
        if type == 'function_url':
            return self._process_function_url_event(event)
        elif type == 'api_gateway_proxy':
            return self._process_api_url_event(event)
        else:
            raise ValueError("Invalid Type")


class LambdaFlask:
    """
    A lightweight Flask-like framework for handling web requests in AWS Lambda.
    """
    def __init__(self, source='function_url', enable_request_logging=True, enable_response_logging=True):
        """
        Initializes the LambdaFlask framework with options for request and response logging.

        :param source: Specifies the type of source (e.g., 'function_url' or 'api_gateway_proxy').
        :param enable_request_logging: Enables logging of request details.
        :param enable_response_logging: Enables logging of response details.
        """
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
        """
        Defines or retrieves a route for specified HTTP methods.

        :param path: URL path to associate with the route.
        :param http_methods: Optional list of HTTP methods to support on this route.
        :return: The route object.
        """
        if path in self.routes:
            route = self.routes[path]
        else:
            route = Route(path, http_methods)
            self.routes[path] = route
        return route

    def process_request(self, event):
        """
        Processes an incoming request event based on the defined routes and methods.

        :param event: Event data containing the request details.
        :return: JSON formatted response from the route handler or error responses.
        """
        response = Response(500, 'Unable To Process Request',
                            isApiGatewayEvent=self.isApiGatewayEvent)
        try:
            req_info = utills().process_event(event, self.source)
            if self.enable_request_logging:
                req_info.log(self.logger)
            if req_info.route() in self.routes:
                route = self.routes[req_info.route()]
                response = route.handle_request(
                    req_info.method(), req_info.params())
            else:
                response = Response(
                    404, 'Route Not Found', isApiGatewayEvent=self.isApiGatewayEvent).json()
        except Exception as e:
            response = Response(
                500, {'error': str(e)}, isApiGatewayEvent=self.isApiGatewayEvent).json()
        if self.enable_response_logging:
            self.log_response(response)
        return Response(response.get('statusCode', 500), response.get('body', {}), response.get('headers', {}), response.get('isBase64Encoded', False), self.isApiGatewayEvent).json()

    def execute_handler(self, handler, req_params):
        """
        Directly executes a handler with the provided request parameters.

        :param handler: The handler function to execute.
        :param req_params: Request parameters to pass to the handler.
        :return: The result from the handler.
        """
        return handler(req_params)

    def get_registered_routes(self):
        """
        Returns a dictionary of all registered routes and their details.

        :return: Dictionary of registered routes.
        """
        return self.routes

    def log_response(self, response):
        """
        Logs the response details using the configured logger.

        :param response: Response data to log.
        """
        if self.logger.isEnabledFor(logging.INFO):
            statusCode, body = response.get('statusCode', 500), response.get(
                'body', 'No Body Recieved in Response')
            self.logger.info(
                "Response - Status Code: %s, Body: %s", statusCode, body)

    def route_decorator(self, path, http_methods=None, middlewares=None, **middleware_kwargs):
        """
        A decorator to simplify the registration of routes and their methods with optional middlewares.

        :param path: Path for the route.
        :param http_methods: List of HTTP methods to handle on this route.
        :param middlewares: Optional list of middleware to apply to the route.
        :param middleware_kwargs: Additional keyword arguments for middleware configuration.
        :return: Decorator function that registers the specified handler and middlewares.
        """
        if middlewares is None:
            middlewares = []

        def decorator(func):
            """
            Decorates and registers the function as a handler for the specified HTTP methods on the given route path.

            :param func: The function to be decorated. This function will handle the HTTP requests for the given route.
            :return: The original function, now registered as a route handler with associated middlewares.
            """
            route = self.route(path, http_methods)
            for http_method in http_methods:
                route.route(http_method, func)
                for middleware in middlewares:
                    route.use_middleware(http_method, middleware)
            return func

        return decorator