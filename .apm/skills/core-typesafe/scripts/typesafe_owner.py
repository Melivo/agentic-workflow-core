"""Small local IO/config boundary for the existing plan owner; no model or dispatch.

load_config reads only the explicit non-secret config and returns (policy, sender).
Nothing sends on import or load. month_end_due is a pure calendar guard, not a
scheduler or a once-only execution guarantee. Owner retains actual schedule receipts.
"""
import calendar
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import typesafe_collection as collection

CONFIG_PATH = Path.home() / '.config/agentic-workflow-core/typesafe.json'
STATE_PATH = Path.home() / '.local/state/agentic-workflow-core/typesafe'
REPORT_ZONE = 'Europe/Berlin'


def load_config(path=CONFIG_PATH):
    """No mkdir, adoption, secret lookup or network. Missing config remains open."""
    value = collection._read_config(path)
    collection._shape(value, ('projects', 'transport'))
    policy = collection.project_policy(value['projects'])
    transport = value['transport']
    collection._shape(transport, ('ssh_target', 'binding', 'remote_script'))
    collection._require(transport['binding'] is not None and transport['remote_script'] is not None,
                        'invalid_configuration')
    sender = collection.SSHSender(transport['ssh_target'], binding=transport['binding'],
                                  remote_script=transport['remote_script'])
    return policy, sender


def month_end_due(when):
    """Aware instant -> last calendar day at local 22:00, before report/data IO."""
    collection._require(isinstance(when, datetime) and when.tzinfo is not None
                        and when.utcoffset() is not None, 'invalid_time')
    local = when.astimezone(ZoneInfo(REPORT_ZONE))
    return (local.day == calendar.monthrange(local.year, local.month)[1]
            and local.hour == 22 and local.minute == 0)
