from csv import DictReader
import os

from django.conf import settings
from django.utils.encoding import smart_text
import requests
import service.control

from services.utils import get_timezone_for_location

from .base import Row


class LocationRow(Row):

    field_names = (
        'office_name',
        'office_address_1',
        'office_address_2',
        'office_city',
        'office_region',
        'office_postal_code',
        'office_country_code',
        'office_image_url',
    )

    def get_protobuf_data(self):
        data = {}
        for key in self.field_names:
            location_key = key.split('office_')[1]
            data[location_key] = self.data[key].strip()
        return data


def get_lat_lng(data):
    address_parts = [p for p in [
        data.get('address_1'),
        data.get('address_2'),
        data.get('city'),
        data.get('region'),
        data.get('postal_code'),
    ] if p]
    address = ','.join(address_parts)
    parameters = {'key': settings.GOOGLE_API_KEY, 'address': address}
    response = requests.get(settings.GOOGLE_GEOCODING_ENDPOINT, params=parameters)
    location = response.json()['results'][0]['geometry']['location']
    return location['lat'], location['lng']


def save_location(location_row, token):
    data = location_row.get_protobuf_data()
    client = service.control.Client('organization', token=token)
    try:
        created = False
        response = client.call_action('get_location', name=data['name'])
    except service.control.CallActionError:
        created = True
        lat, lng = get_lat_lng(data)
        data['latitude'] = str(lat)
        data['longitude'] = str(lng)
        timezone = get_timezone_for_location(lat, lng)
        data['timezone'] = timezone
        response = client.call_action('create_location', location=data)
    return response.result.location, created


def add_locations(filename, token):
    locations = []
    if os.path.exists(filename):
        with open(filename) as read_file:
            reader = DictReader(read_file)
            for row_data in reader:
                row = LocationRow(row_data)
                if not row.is_empty():
                    location, created = save_location(row, token)
                    if created:
                        print 'successfully added location: %s' % (location.name,)
                    else:
                        print 'location already exists: %s' % (location.name,)
                    locations.append(location)
    return locations
