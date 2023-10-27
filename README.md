# PyLambdAPI

**PyLambdAPI** is a lightweight Python framework designed explicitly for AWS Lambda functions. It provides a streamlined approach to building serverless web services, offering the flexibility to create API endpoints accessible through either function URLs or API Gateway. If you're seeking a simplified alternative to complex web frameworks like Flask for Lambda-based microservices, PyLambdAPI is the solution you've been looking for.

## Why PyLambdAPI?

**AWS Lambda** is a potent and scalable serverless computing platform. However, building API endpoints with AWS Lambda often involves dealing with various input sources, request management, and response structuring. PyLambdAPI simplifies this process and stands out for these reasons:

- **Lightweight**: PyLambdAPI is intentionally kept minimal and user-friendly, without added complexities.
- **AWS Lambda Compatibility**: It's purpose-built for AWS Lambda, taking into account the unique characteristics of serverless environments.
- **Support for Function URL and API Gateway**: PyLambdAPI adeptly handles requests from both function URLs and API Gateway.
- **Middleware Support**: Easily incorporate middleware functions into your routes for custom request and response processing.
- **Logging**: PyLambdAPI comes with built-in request and response logging, simplifying troubleshooting.
- **Flexible Routing**: Define API routes with various HTTP methods using a straightforward and intuitive syntax.

## Installation

To install PyLambdAPI using `pip`:

```bash
pip install pylambdapi
```

## Getting Started

To create a serverless API with PyLambdAPI, follow these steps:

1. Import the `LambdaFlask` class from the library.
2. Create a `LambdaFlask` instance.
3. Define your routes and route handlers.
4. Deploy your Lambda function, and your API is ready to roll!

```python
from pylambdapi import LambdaFlask

# Create a LambdaFlask instance
app = LambdaFlask(source='function_url')

# Define a route and a route handler
@app.route_decorator('/hello', http_methods=['GET'])
def hello():
    return 'Hello, Lambda World!'

# Deploy your Lambda function and configure your API Gateway or function URL to point to it.
```

## Routing and Handlers

PyLambdAPI employs a straightforward route and handler definition. You can specify HTTP methods, create middleware, and structure your response with ease.

```python
# Define a route and a route handler
@app.route_decorator('/users', http_methods=['GET', 'POST'])
def users():
    # Handle GET or POST requests here
    # Return your response

# Add middleware to a route
@app.route_decorator('/private', http_methods=['GET'], middlewares=[MyCustomMiddleware()])
def private_route():
    # Middleware processes the request before reaching this handler
    # Handle the request and return a response
```



## Logging

PyLambdAPI offers built-in request and response logging for effortless troubleshooting. You can enable or disable request and response logging as needed.

```python
app = LambdaFlask(source='api_gateway_proxy', enable_request_logging=True, enable_response_logging=False)
```

## Handling Path Parameters

PyLambdAPI supports path parameters. Here's an example of a route that accepts a dynamic username:

```python
@app.route_decorator('/user/{username}', http_methods=['GET'])
def get_user(req_params):
    username = req_params.get('username')
    # Logic to fetch user by username
    return Response(200, f"Fetching details for {username}")
```

## Middleware

You can include custom middleware functions to process requests and responses before they reach the route handler. Middleware provides flexibility in managing various aspects of your API, such as authentication, data validation, or response formatting.

```python
class MyCustomMiddleware:
    def process_request(self, req_params):
        # Process the request before reaching the route handler
        return req_params

    def process_response(self, response):
        # Process the response before returning it
        return response
```

## Route Access

PyLambdAPI supports both function URLs and API Gateway. You can choose the source that best suits your use case.

```python
# Initialize LambdaFlask for function URL
app = LambdaFlask(source='function_url')

# Initialize LambdaFlask for API Gateway
app = LambdaFlask(source='api_gateway_proxy')
```

## Contributing
This framework is open source and new; feel free to contribute by improving documentation, adding new features, requesting new features, or fixing bugs. To contribute, fork this repository and submit a pull request with your changes. Your contributions will be greatly appreciated!

## License

PyLambdAPI is released under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for more details.

## Contact

For questions or issues, please feel free to open a GitHub issue or reach out at [kushagraindurkhya7@gmail.com](mailto:kushagraindurkhya7@gmail.com).

## Acknowledgments

I created PyLambdAPI to simplify the process of building APIs for AWS Lambda functions. I hope it makes your serverless development experience more enjoyable.

---

*Disclaimer: PyLambdAPI is not an official AWS product but a third-party library developed to simplify API creation for AWS Lambda.*
