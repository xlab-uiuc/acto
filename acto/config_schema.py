import os
from typing import Literal

from pydantic import BaseModel


class AlarmsConfig(BaseModel):
    warning_in_operator_logs: bool = False


class NotificationsConfig(BaseModel):
    enabled: bool = False


class StateCheckerConfig(BaseModel):
    enable_canonicalization: bool = True


class CheckersConfig(BaseModel):
    state: StateCheckerConfig


class RayConfig(BaseModel):
    enabled: bool = True
    ansible_inventory: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts',
                                          'ansible', 'ansible_hosts')


class Config(BaseModel):
    alarms: AlarmsConfig
    checkers: CheckersConfig
    mode: Literal['whitebox', 'blackbox'] = 'whitebox'
    notifications: NotificationsConfig
    strict: bool = True
    ray: RayConfig
