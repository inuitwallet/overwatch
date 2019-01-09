from datetime import timedelta

BEAT_SCHEDULE = {
    'cloud-watch-logs': {
        'type': 'get.cloudwatch.logs',
        'schedule': timedelta(seconds=30)
    },
}
