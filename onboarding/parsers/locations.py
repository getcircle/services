from csv import DictReader
import os

from django.conf import settings
from django.utils.encoding import smart_text
import requests
import service.control

from services.utils import get_timezone_for_location


class LocationRow(object):

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

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        if key in self.data:
            return smart_text(self.data[key])

        return super(LocationRow, self).__getattr__(key)

    def get_protobuf_data(self):
        data = {}
        for key in self.field_names:
            location_key = key.split('office_')[1]
            data[location_key] = self.data[key]
        return data

    def is_empty(self):
        return not any(self.data.values())


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


def save_location(organization_client, organization_id, location_row):
    data = location_row.get_protobuf_data()
    lat, lng = get_lat_lng(data)
    data['latitude'] = str(lat)
    data['longitude'] = str(lng)
    timezone = get_timezone_for_location(lat, lng)
    data['organization_id'] = organization_id
    data['timezone'] = timezone
    try:
        created = True
        response = organization_client.call_action('create_location', location=data)
    except service.control.CallActionError:
        created = False
        response = organization_client.call_action('get_location', name=data['name'])
    return created, response.result.location


def add_locations(organization_client, organization_id, filename):
    locations = []
    if os.path.exists(filename):
        with open(filename) as read_file:
            reader = DictReader(read_file)
            for row_data in reader:
                row = LocationRow(row_data)
                if not row.is_empty():
                    created, location = save_location(organization_client, organization_id, row)
                    if created:
                        print 'successfully added location: %s' % (location.name,)
                    else:
                        print 'location already exists: %s' % (location.name,)
                    locations.append(location)
    return locations
