# Nebulae

## Prerequisites

### Git

Ensure you have git initialised for the project, as some build tools require a git commit to tag a docker image

### Docker

Ensure Docker is installed and running.

### Nebulae

Install `Nebulae` using:

```shell
bin/run-once/install-nebulae.sh
```

## How to run locally

The easiest way to run this locally is via

```shell
atlas nebulae start
```

This command will automatically build your application, package it in a Docker image, and run it within a Nebulae sandbox.

## Included functionality


### SLAuth

Nebulae is configured to use the SLAuth sidecar for authentication.

The `slauth-mock-sidecar` is a docker image that will proxy requests to your service, injecting SLAuth headers on all requests. You can configure these headers to emulate different users via the control panel.

You can ping your services healthcheck through the `slauth-mock-sidecar` via:

```shell
curl http://localhost:8080/healthcheck
```

For authenticated endpoints, you will need to configure authenticated requests via the control panel at [localhost:9090](http://localhost:9090/).

You can find more docs on using the mock sidecar [on DAC](https://developer.atlassian.com/platform/slauth/testing/nebulae/).

### Local or remote resources

You can run your service on your workstation, but connect to local or remote AWS resources like RDS, SQS, S3 and others.

Use the below example to start a sandbox with local resources:

```shell
atlas nebulae start --export-env=envvars.env --sandbox=environmentOnly
```

Or this one to connect to remote resources in ddev:
:warning: You need to make sure you have already deployed your service to ddev for those resources to exist.

```shell
atlas nebulae start --export-env=envvars.env --sandbox=environmentOnly --all-remote
```

Finally, start your service locally via your IDE or framework command.
To export the same environment variables as nebulae used, be sure to run the following before you start your service:

```shell
source envvars.env
```

## More Info

For more information on using Nebulae go to [DAC](http://go/nebulae)
