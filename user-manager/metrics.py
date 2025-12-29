import socket
from prometheus_client import Gauge, Counter

HOSTNAME = socket.gethostname()
SERVICE_NAME = "user-manager"

CLEANUP_DURATION = Gauge(
    'cleanup_duration_seconds',
    'Time spent cleaning up expired messages',
    ['service', 'node']
)

MESSAGES_CLEANED_TOTAL = Counter(
    'messages_cleaned_total',
    'Total number of expired messages cleaned',
    ['service', 'node']
)

USER_REGISTRATION_ERRORS_TOTAL = Counter(
    'user_registration_errors_total',
    'Total number of errors during user registration',
    ['service', 'node', 'error_type']
)
