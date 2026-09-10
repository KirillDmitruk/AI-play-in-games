from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from agent import validate_plan, request
from settings import Settings
from game import SnakeGame


class AgentTests(unittest.TestCase):
    def test_strict_format(self):
        self.assertEqual(validate_plan('{"actions":["RIGHT","DOWN"]}', 3), ['RIGHT', 'DOWN'])
        for text in ('UP', '{}', '{"actions":[]}', '{"actions":["Go UP"]}',
                     '{"actions":["up"]}', '{"actions":[null]}', '{"actions":[[1]]}',
                     '{"actions":["UP"],"reason":"hello"}', '{"actions":["UP","UP","UP","UP"]}'):
            with self.assertRaises((ValueError, TypeError)):
                validate_plan(text, 3)

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_key_is_not_import_error(self):
        self.assertIn('GEMINI_API_KEY', request(Settings(), SnakeGame().snapshot()).error)

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-only'})
    def test_sdk_config_and_usage_of_malformed_response(self):
        from google.genai import types
        u = types.GenerateContentResponseUsageMetadata(prompt_token_count=10,
            candidates_token_count=2, thoughts_token_count=0, total_token_count=12)
        response = types.GenerateContentResponse(candidates=[types.Candidate(
            finish_reason='STOP', content=types.Content(parts=[types.Part(text='{"actions": []}')]))],
            usage_metadata=u)
        with patch('google.genai.Client') as client:
            client.return_value.models.generate_content.return_value = response
            result = request(Settings(), SnakeGame().snapshot())
            self.assertIsNotNone(result.error)
            self.assertEqual(result.usage['total'], 12)
            conf = client.return_value.models.generate_content.call_args.kwargs['config']
            self.assertEqual(conf.thinking_config.thinking_budget, 0)
            self.assertEqual(conf.max_output_tokens, 128)
            self.assertEqual(client.call_args.kwargs['http_options'].retry_options.attempts, 1)
            client.return_value.close.assert_called_once()

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-only'})
    def test_truncated_json_never_moves(self):
        from google.genai import types
        r = types.GenerateContentResponse(candidates=[types.Candidate(finish_reason='MAX_TOKENS',
            content=types.Content(parts=[types.Part(text='{"actions":["UP"]}')]))])
        with patch('google.genai.Client') as client:
            client.return_value.models.generate_content.return_value = r
            reply = request(Settings(), SnakeGame().snapshot())
            self.assertEqual(reply.actions, [])
            self.assertIsNotNone(reply.error)

    def test_settings_validation(self):
        for field, value in [('plan_length', 6), ('max_retries', -1), ('thinking_budget', -1),
                             ('max_session_requests', 0), ('model', 'other'), ('max_output_tokens', 2)]:
            with self.assertRaises(ValueError):
                replace(Settings(), **{field: value})
