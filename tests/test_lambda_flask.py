# import unittest
# import json
# from PyLambdAPI.lambda_flask import LambdaFlask

# class TestLambdaFlask(unittest.TestCase):
#     def setUp(self):
#         self.app = LambdaFlask()

    # def test_route_decorator(self):
    #     @self.app.route('/test')
    #     def test_handler(params):
    #         return {'statusCode': 200, 'body': json.dumps('Test Route')}
        
    #     self.assertIn('/test', self.app.routes)
    #     route_info = self.app.routes['/test']
    #     self.assertEqual(len(route_info['handlers']), 1)
    #     self.assertTrue('GET' in route_info['handlers'])
    #     self.assertIsNone(route_info['auth_check'])

    # def test_default_decode_header(self):
    #     event = {'headers': {'Authorization': 'Bearer Token'}}
    #     user_attributes = self.app.default_decode_header(event)
    #     self.assertEqual(user_attributes, {'token': 'Token'})

    # def test_default_auth_check(self):
    #     user_attributes = {'token': 'ValidToken'}
    #     self.assertTrue(self.app.default_auth_check(user_attributes))
        
#     def test_aggregate_params(self):
#         event = {
#             'queryStringParameters': {'param1': 'value1'},
#             'body': '{"param2": "value2"}',
#             'isBase64Encoded': False
#         }
#         params = self.app.aggregate_params(event)
#         self.assertEqual(params, {'param1': 'value1', 'param2': 'value2'})

#     def test_process_request(self):
#         @self.app.route('/test')
#         def test_handler(params):
#             return {'statusCode': 200, 'body': json.dumps(params)}
        
#         event = {
#             'requestContext': {'http': {'path': '/test'}},
#             'httpMethod': 'GET',
#             'queryStringParameters': {'param1': 'value1'},
#             'body': json.dumps({'param2': 'value2'})
#         }
        
#         response = self.app.process_request(event)
#         self.assertEqual(response['statusCode'], 200)
#         self.assertEqual(json.loads(response['body']), {'param1': 'value1', 'param2': 'value2'})

#     # Add more tests as needed

# if __name__ == '__main__':
#     unittest.main()
