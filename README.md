services
=====

rhlabs services

## Setup

We run our services using github.com/remind101/empire. The following steps will bring up the services from scratch. They assume that you've set up the empire working environment correctly and have logged into our instance of empire at https://empire.circlehq.co.

1. Create the api service

  ```
  $ emp create services
  ```
  
2. Add the api.circlehq.co domain

  ```
  $ emp domain-add -a services api.circlehq.co
  ```
  
3. Add the api.circlehq.co SSL cert

  ```
  $ emp ssl-cert-add -a services api_circlehq_co.crt key.pem
  ```
  
4. Load the environmental variables

  ```
  $ emp env-load -a services app.env
  ```
  
5. Deploy the services docker image (this image should be built by CircleCI after each push to master)

  ```
  $ emp deploy -a services mhahn/services
  ```

6. Create an app to run migrations

  ```
  $ emp create services-migrations
  $ emp env-load -a services-migrations app.env
  $ emp deploy -a services-migrations mhahn/services
  ```

7. Run initial migrations

  ```
  $ emp run -a services bash
  > python manage.py migrate
  ```

## Deploying

Our [CircleCI](https://circleci.com/gh/getcircle/services) job handles building and pushing the `mhahn/services` docker image after each push to master (if the tests succeed). You should receive a notification in the #circle-ci slack channel when the build is successfully pushed to our private docker repo.

Once the image has been pushed to the docker repo, you can deploy with:

```
$ emp deploy -a services mhahn/services
```

If the release requires migrations, you want to release and run those against the `services-migrations` app before deploying to `services`.

```
$ emp deploy -a services-migrations mhahn/services
$ emp run -a services-migartions python manage.py migrate --no-input
```

Once the migrations have been run you can release to `services` as usual.

## Updating configs

To add a config for the app:

```
$ emp set FOO=BAR
```

To remove a config:
```
$ emp unset FOO=BAR
```
