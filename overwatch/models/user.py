import hashlib
import hmac
import uuid

from django.db import models


class ApiProfile(models.Model):
    api_user = models.UUIDField(default=uuid.uuid4)
    api_secret = models.UUIDField(default=uuid.uuid4)
    last_nonce = models.BigIntegerField(default=0)

    def __str__(self):
        return self.api_user.hex

    def auth(self, supplied_hash, nonce):
        # check that the supplied nonce is an integer
        # and is greater than the last supplied nonce to prevent reuse
        try:
            nonce = int(nonce)
        except ValueError:
            return False, "n parameter needs to be a positive integer"

        if nonce <= self.last_nonce:
            return (
                False,
                "n parameter needs to be a positive integer and greater than the previous nonce",
            )

        # calculate the hash from our own data
        calculated_hash = hmac.new(
            self.api_secret.bytes,
            "{}{}".format(self.api_user.hex.lower(), nonce).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # update the last nonce value
        self.last_nonce = nonce
        self.save()

        if calculated_hash != supplied_hash:
            return False, "supplied hash does not match calculated hash"

        return True, "authenticated"
