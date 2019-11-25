import logging
import sys

import requests

logger = logging.getLogger()

for h in logger.handlers:
    logger.removeHandler(h)

h = logging.StreamHandler(sys.stdout)
h.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

logger.addHandler(h)
logger.setLevel(logging.INFO)


def vigil_alert(alert_channel_id, data):
    r = requests.post(
        url='https://vigil.crypto-daio.co.uk/alert/{}'.format(alert_channel_id),
        data=data
    )

    if r.status_code != requests.codes.ok:
        logger.error('vigil gave a bad response code: {}'.format(r.status_code))
        return False

    try:
        response = r.json()
    except ValueError:
        logger.error('vigil did not return valid JSON: {}'.format(r.text))
        return False

    if not response.get('success'):
        logger.error('vigil did not report a success: {}'.format(response))
        return False

    logger.info('successfully alerted {} through vigil'.format(data))
    return True
