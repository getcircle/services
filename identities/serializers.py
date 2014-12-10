from rest_framework import serializers
from . import models


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Identity
