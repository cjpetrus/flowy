import unittest
from boto.swf.layer1 import Layer1
from mock import patch
import json
from functools import partial


def mock_json_values(action, data, object_hook=None, requests=[],
                     responses=[]):
    try:
        requests.append((action, data))
        resp = responses.pop(0)
        return resp[1]
    except IndexError:
        return None


def load_json_responses(file_name):
    """
    Patch Layer1 make_request to return the contents of file_name
    """
    f = open(file_name, "rb")
    responses = map(json.loads, f.readlines())
    f.close()
    requests = []
    f = partial(mock_json_values, requests=requests, responses=responses)
    def decorator(test_item):
        @patch.object(Layer1, 'json_request', f)
        def w(self):
            return test_item(self, requests)
        return w
    return decorator


@patch.object(Layer1, '__init__', lambda *args: None)
class WorkflowTestCase(unittest.TestCase):

    def assertCompletedWorkflow(self, requests):
        self.assertEqual(requests[-1][1]['decisions'][0]['decisionType'],
                         'CompleteWorkflowExecution')
        self.assertEqual(len(requests[-1][1]['decisions']), 1)

    def assertFailedWorkflow(self, requests):
        self.assertEqual(requests[-1][1]['decisions'][0]['decisionType'],
                         'FailWorkflowExecution')
        self.assertEqual(len(requests[-1][1]['decisions']), 1)
