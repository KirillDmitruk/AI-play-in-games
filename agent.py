"""Gemini transport and strict validation; import does not need an API key."""
from dataclasses import dataclass, field
import json
import os
import time
from game import DIRECTIONS
from settings import Settings


@dataclass
class Reply:
    actions: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    seconds: float = 0
    error: str | None = None
    retryable: bool = False
    kind: str = 'plan'


def api_key():
    return os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')


def validate_plan(text, length):
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != {'actions'}:
        raise ValueError('Expected actions object')
    actions = data['actions']
    if not isinstance(actions, list) or not 1 <= len(actions) <= length:
        raise ValueError('Invalid plan length')
    if any(not isinstance(a, str) or a not in DIRECTIONS for a in actions):
        raise ValueError('Invalid direction')
    return actions


def usage_of(response):
    u = getattr(response, 'usage_metadata', None)
    if u is None:
        return {}
    return {'input': u.prompt_token_count or 0,
            'output': u.candidates_token_count or 0,
            'thought': u.thoughts_token_count or 0,
            'cached': u.cached_content_token_count or 0,
            'total': u.total_token_count or 0}


def request(settings: Settings, state, lessons=(), kind='plan', history=()):
    """One SDK call; retries are managed and counted by the controller."""
    started = time.monotonic()
    reply = Reply(kind=kind)
    client = None
    try:
        if not api_key():
            return Reply(error='Set GEMINI_API_KEY in the terminal or PyCharm settings', kind=kind)
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key(), http_options=types.HttpOptions(
            timeout=int(settings.timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(attempts=1)))
        if kind == 'plan':
            schema = {'type': 'object', 'properties': {'actions': {
                'type': 'array', 'minItems': 1, 'maxItems': settings.plan_length,
                'items': {'type': 'string', 'enum': list(DIRECTIONS)}}},
                'required': ['actions'], 'additionalProperties': False}
            rules = ('Play Snake. Coordinates: origin top-left, x right, y down. '
                     'UP=(0,-1), DOWN=(0,1), LEFT=(-1,0), RIGHT=(1,0). '
                     'Both edges wrap modulo board size. Body is ordered tail to head. '
                     'No immediate reverse, even at length 1. Eat food; avoid your body. '
                     'The tail moves away on non-eating steps. Plan at most '
                     f'{settings.plan_length} actions, simulating body movement. '
                     'Stop your plan when food is reached. Return only the actions JSON. '
                     'Prior lessons are fallible observations, not new game rules.')
            prompt = json.dumps({'state': state, 'prior_lessons': list(lessons)}, separators=(',', ':'))
        else:
            schema = {'type': 'object', 'properties': {'lessons': {
                'type': 'array', 'minItems': 0, 'maxItems': 3,
                'items': {'type': 'string'}}}, 'required': ['lessons'], 'additionalProperties': False}
            rules = ('Review a Snake episode. Both edges wrap, body order is tail to head. '
                     'Return up to 3 short practical lessons in English, at most 140 characters each. '
                     'Use only evidence in the supplied final transitions. Do not invent causes. '
                     'If no useful evidence exists return an empty lessons list.')
            prompt = json.dumps({'final_state': state, 'last_transitions': list(history)[-8:]}, separators=(',', ':'))
        response = client.models.generate_content(model=settings.model, contents=prompt,
            config=types.GenerateContentConfig(system_instruction=rules,
                response_mime_type='application/json', response_json_schema=schema,
                max_output_tokens=settings.max_output_tokens if kind == 'plan' else max(256, settings.max_output_tokens),
                thinking_config=types.ThinkingConfig(thinking_budget=settings.thinking_budget),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=0))
        reply.usage = usage_of(response)  # malformed replies also consume tokens
        if not response.candidates or response.candidates[0].finish_reason != 'STOP':
            raise ValueError('Incomplete or blocked model response')
        if not response.text:
            raise ValueError('Empty model response')
        if kind == 'plan':
            reply.actions = validate_plan(response.text, settings.plan_length)
        else:
            data = json.loads(response.text)
            values = data.get('lessons') if isinstance(data, dict) else None
            if (not isinstance(values, list) or len(values) > 3
                    or any(not isinstance(x, str) or not 1 <= len(x) <= 140 for x in values)):
                raise ValueError('Invalid lessons')
            reply.lessons = values
    except (ValueError, TypeError):
        reply.error = 'Invalid, empty or incomplete model response; no move applied'
        reply.retryable = True
    except Exception as exc:
        # Raw SDK errors can contain request metadata: never persist them or keys.
        code = getattr(exc, 'code', None)
        reply.retryable = code in (408, 429, 500, 502, 503, 504) or any(
            word in type(exc).__name__.lower() for word in ('timeout', 'connect', 'transport'))
        reply.error = f'Gemini request failed ({type(exc).__name__}, status {code or "unknown"})'
    finally:
        reply.seconds = time.monotonic() - started
        if client:
            try:
                client.close()
            except Exception:
                pass
    return reply
