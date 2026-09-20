# Spinnaker

For more info on how Spinnaker works see the [DAC docs](https://developer.atlassian.com/platform/spinnaker/).

## Onboarding

For onboarding to spinnaker, visit the [Onboarding docs](https://developer.atlassian.com/platform/spinnaker/overview/onboarding/).

After completing the script, you will have your own [Default Pipeline](https://developer.atlassian.com/platform/spinnaker/default-pipelines/getting-started/), which are ready-made pipelines that can be used to deploy your service with a best practice deployment workflow.

If this doesn't match your deployment needs, consider [Custom Pipelines](https://developer.atlassian.com/platform/spinnaker/custom-pipelines/getting-started/) for a more configurable pipeline.

## Public Holidays

Spinnaker offers the ability to block deployments during your team's public holiday time. This means your team gets to enjoy safer changes that only occur during your
business hours, and much more peaceful on-call rotations.

By default we can't figure out what public holidays would apply to your team, but you can configure this in the

```yaml
publicHolidays: []
```

property inside your `default-pipelines.spinnaker.yaml`.
See [Public Holidays](https://developer.atlassian.com/platform/spinnaker/default-pipelines/safe-release/#public-holidays) documentation to see how to enable this for your team!

## Deploying

`bitbucket-pipelines.yml` file already has steps to deploy to `ddev` in spinnaker. Feel free to modify the step or change the `default-pipelines.spinnaker.yml` file to add more environments.
After running the Spinnaker step in a pipeline, check the status of your deployments [here](https://spinnaker-prod.internal.shared-prod.us-east-1.kitt-inf.net/#/applications/proactive-ai-platform/executions/).

To deploy via Spinnaker outside of a pipeline you will need to run: `bin/get-deployment-access.sh` and `bin/spinnaker-deploy.sh`

### Manual Pipeline Configuration

If you wish to manually add the step to your pipeline, you can use the following:

```
- name: Tag Policy to dev
  deployment: poco-dev
  headPipes:
    - pipe: atlassian/artifactory-sidekick:v1
      variables: {}
  scriptBody:
    - source .artifactory/activate.sh
  tailPipes:
    - pipe: docker://docker.atl-paas.net/atlassian/poco-pipe:latest
      variables:
        POLICIES: build/resources/main/policies/service/policy.json
        TESTS: build/resources/main/policies/tests.json
        LABEL: proactive-ai-platform-${BITBUCKET_COMMIT}
        SERVICE_NAME: proactive-ai-platform
        COMPLIANT: "false"
- name: Deploy via Spinnaker
  deployment: spinnaker
  headPipes:
    - pipe: docker://atlassian/artifactory-sidekick:latest
  scriptBody:
    - source .artifactory/activate.sh
  tailPipes:
    - pipe: docker://docker.atl-paas.net/atlassian/spinnaker-deploy:latest
      variables:
        BEFORE_SCRIPT: export DOCKER_TAG=${BITBUCKET_COMMIT}
        SERVICE_NAME: proactive-ai-platform
        SERVICE_DESCRIPTOR: service-descriptor.sd.yml
        METADATA: --metadata=poco-bundle-tag=proactive-ai-platform-${BITBUCKET_COMMIT}

```

You will also need to ensure that you create a spinnaker deployment environment in bitbucket.

### Staging and Production

To deploy to staging or production environments, you will need to enable a few compliance-related settings.
You can check more about sox-compliance [here](https://hello.atlassian.net/wiki/spaces/RELENG/pages/1271107592/HOWTO+enable+Compliance+controls+and+secure+your+repository).

The following example will enable deployment into ddev and stg-west2 environments.


```yaml
schemaVersion: '1'
timeZone: Australia/Sydney
publicHolidays:
  - AU/NSW

pipelines:
  - enabled: true
    deployDuring: {}
    environments:
      - ddev
      - stg-west2
    namespace: spinnaker-proactive-ai-platform
    serviceDescriptorTag: service-descriptor
    slackChannel: dev-null
    template: stagedDeploys
    extensions:
      - before: staging
        stage:
          name: Poco Tag bundle in staging
          alias: preconfiguredWebhook
          type: pocoTagBundle
          parameterValues:
            env: staging
            kind: slauth
            label: '${execution.trigger.artifacts[0].metadata.objectMetadata.custom["poco-bundle-tag"]}'
            namespace: poco-dev
            region: ''
            service_name: proactive-ai-platform
```


## Troubleshooting

- `Error occurred uploading default pipelines: Could not find generators after 5 minutes`

  SLAuth takes a while to update SSAM group caches, so if you've recently registered your service with Micros, waiting a little longer might resolve things.

- `My Bitbucket Pipeline has passed, but my component is not deployed`

  Spinnaker manages deployments separately, and will not report failures back to Bitbucket. Check the status of your deployments [here](https://spinnaker-prod.internal.shared-prod.us-east-1.kitt-inf.net/#/applications/proactive-ai-platform/executions/). Consider enabling [notifications](https://developer.atlassian.com/platform/spinnaker/default-pipelines/staged-deploys/#notifications) for failed deployments.
