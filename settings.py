"""Explicit limits. The API key is deliberately not part of this object."""
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model: str = 'gemini-2.5-flash'
    plan_length: int = 3
    thinking_budget: int = 0
    max_output_tokens: int = 128
    timeout_seconds: float = 30
    max_retries: int = 2
    retry_delay_seconds: float = 1
    steps_per_second: float = 5
    max_steps: int = 2000
    max_idle_steps: int = 200
    max_episode_requests: int = 100
    max_session_requests: int = 200
    max_session_tokens: int = 50000
    memory: bool = False

    def __post_init__(self):
        if self.model != 'gemini-2.5-flash':
            raise ValueError('This version supports gemini-2.5-flash only')
        for name in ('plan_length', 'max_output_tokens', 'thinking_budget', 'max_retries',
                     'max_steps', 'max_idle_steps', 'max_episode_requests',
                     'max_session_requests', 'max_session_tokens'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name} must be an integer')
        if not 1 <= self.plan_length <= 5:
            raise ValueError('plan_length must be between 1 and 5')
        if not (self.thinking_budget == 0 or 128 <= self.thinking_budget <= 24576):
            raise ValueError('thinking_budget must be 0 or 128..24576')
        if not 64 <= self.max_output_tokens <= 4096:
            raise ValueError('max_output_tokens must be 64..4096')
        if self.thinking_budget >= self.max_output_tokens:
            raise ValueError('max_output_tokens must exceed thinking_budget')
        if not 0 <= self.max_retries <= 3:
            raise ValueError('max_retries must be 0..3')
        if not 1 <= self.timeout_seconds <= 120:
            raise ValueError('timeout_seconds must be 1..120')
        if not 0.1 <= self.steps_per_second <= 30 or not 0 <= self.retry_delay_seconds <= 30:
            raise ValueError('Invalid speed or retry delay')
        for name in ('max_steps', 'max_idle_steps', 'max_episode_requests',
                     'max_session_requests', 'max_session_tokens'):
            if getattr(self, name) < 1:
                raise ValueError(f'{name} must be positive')
        if type(self.memory) is not bool:
            raise ValueError('memory must be true or false')

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else {}
        if not isinstance(data, dict):
            raise ValueError('Settings must be a JSON object')
        return cls(**data)

    def as_dict(self):
        return asdict(self)
