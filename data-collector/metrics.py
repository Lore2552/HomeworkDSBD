from prometheus_client import Gauge, Counter
import socket

HOSTNAME = socket.gethostname()
SERVICE_NAME = "data-collector"

FLIGHT_COLLECTION_DURATION = Gauge(
    'flight_collection_duration_seconds',
    'Time spent collecting flights',
    ['service', 'node']
)

FLIGHTS_COLLECTED_TOTAL = Counter(
    'flights_collected_total',
    'Total number of flights collected',
    ['service', 'node']
)

COLLECTION_ERRORS_TOTAL = Counter(
    'collection_errors_total',
    'Total number of errors during flight collection',
    ['service', 'node', 'error_type']
)

