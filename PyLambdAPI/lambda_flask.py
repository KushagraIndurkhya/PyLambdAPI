import json
import logging
import base64
class Response:
    def __init__(self) -> None:
        pass
class LambdaFlask:
    def __init__(self, decode_header_fn=None, auth_check_fn=None, enable_request_logging=True, enable_response_logging=True):
        self.routes = {}
        self.decode_header = decode_header_fn or self.default_decode_header
        self.auth_check = auth_check_fn or self.default_auth_check
        self.enable_request_logging = enable_request_logging
        self.enable_response_logging = enable_response_logging
        self.logger = logging.getLogger(__name__)

    def route(self, path, http_methods=None, auth_check=None):
        if http_methods is None:
            http_methods = ['GET']

        def decorator(func):
            self.routes[path] = {
                'handlers': {method: func for method in http_methods},
                'auth_check': auth_check or self.auth_check
            }
            return func
        return decorator

    def process_request(self, event):
        response = {
            'statusCode': 500,
            'body': json.dumps('Internal Server Error')
        }
        try:
            reqPath = event['requestContext']['http']['path']
            method = event['requestContext']['http']['method']
            reqParams = self.aggregate_params(event)
            user_attributes = self.decode_header(event)

            if self.enable_request_logging:
                self.log_request(method, reqPath, reqParams, user_attributes)

            if reqPath in self.routes:
                route_info = self.routes[reqPath]
                if method in route_info['handlers']:
                    handler = route_info['handlers'][method]
                    if route_info['auth_check'](user_attributes):
                        response = self.execute_handler(handler, reqParams)
                    else:
                        response = self.unauthorized_response()
                else:
                    response = self.method_not_allowed_response()
            else:
                response = self.not_found_response()
        except Exception as e:
            response = self.error_response(str(e))

        if self.enable_response_logging:
            self.log_response(response)

        return response
    def log_request(self, method, path, params, user_attributes):
        self.logger.info(f"Request - Method: {method}, Path: {path}, Params: {params}, User: {user_attributes}")

    def log_response(self, response):
        self.logger.info(f"Response - Status Code: {response['statusCode']}, Body: {response['body']}")
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
        return params

    def default_decode_header(self, event):
        # Implementation of your decode_header function
        pass

    def default_auth_check(self, user_attributes):
        # Default implementation of authentication check
        return True

    def unauthorized_response(self):
        return {
            'statusCode': 401,
            'body': json.dumps('Unauthorized')
        }

    def method_not_allowed_response(self):
        return {
            'statusCode': 405,
            'body': json.dumps('Method Not Allowed')
        }

    def not_found_response(self):
        return {
            'statusCode': 404,
            'body': json.dumps('Route Not Found')
        }

    def error_response(self, error_message):
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        }


