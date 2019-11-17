import requests


def vigil_alert(alert_channel_id, data):
    r = requests.post(
        url='https://vigil.crypto-daio.co.uk/alert/{}'.format(alert_channel_id),
        data=data
    )

    if r.status_code != requests.codes.ok:
        print('vigil gave a bad response code: {}'.format(r.status_code))
        return False

    try:
        response = r.json()
    except ValueError:
        print('vigil did not return valid JSON: {}'.format(r.text))
        return False

    if not response.get('success'):
        print('vigil did not report a success: {}'.format(response))
        return False

    print('successfully alerted {} through vigil'.format(data))
    return True
