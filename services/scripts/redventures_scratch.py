from csv import (
    DictReader,
    DictWriter,
)
import hashlib
import os

import boto
from boto.s3.key import Key


IMAGE_BASE_PATH = '/Users/mhahn/Downloads/corporate_photos'
FILENAME = '/Users/mhahn/labs/services/corporate-employee-export-10-7.csv'


def upload_image(bucket, email, image_name):
    identifier = 'profiles/%s' % (hashlib.md5(email).hexdigest(),)
    result = 'https://s3.amazonaws.com/lunohq-media/' + identifier
    if bucket.get_key(identifier):
        print 'key: %s already exists, skipping...' % (identifier,)
    else:
        key = Key(bucket)
        key.key = identifier
        path = os.path.join(IMAGE_BASE_PATH, image_name)
        if os.path.exists(path):
            print 'uploading image: %s' % (path,)
            key.set_contents_from_filename(path)
            print 'finished: %s' % (result,)
        else:
            print 'couldn\'t find photo at: %s' % (path,)
            return None
    return result

with open(FILENAME) as csvfile:
    reader = DictReader(csvfile)
    data = [row for row in reader]

connection = boto.connect_s3()
bucket = connection.get_bucket('lunohq-media')

for record in data:
    image_name = record['profile_picture_image_url'].strip()
    if image_name:
        image_url = upload_image(bucket, record['email'], image_name)
        if image_url:
            record['profile_picture_image_url'] = image_url

with open('output.csv', 'w') as write_file:
    writer = DictWriter(write_file, fieldnames=data[0].keys(), extrasaction='ignore')
    writer.writeheader()
    for row in data:
        writer.writerow(row)
