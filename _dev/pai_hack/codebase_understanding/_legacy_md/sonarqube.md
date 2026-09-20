Set up SonarQube scanning and coverage reporting

## Running Sonar Scan locally

Once you have the config, you can run scans locally by using the Atlas CLI plugin:

```
atlas plugin install -n sonar
atlas sonar scan --defaultBranch main
```

## Running SonarQube for branch and pull request analysis ([docs](https://developer.atlassian.com/platform/tool/sonarqube/branch-pr-analysis/))

If you are not scaffolding out a completely new service using the Paved Path Tool(deprecated), unfortunately there are some manual steps that need to be followed in order to finish the setup process for SonarQube.

### Adding Jacoco:

SonarQube will read the coverage reports from other tools, for JVM services you can use Jacoco.
Jacoco is already included in the project template. This simplifies the setup process, as the necessary configurations are in place.

Once Jacoco is set up, during the `package` phase coverage reports will be produced, which SonarQube can then pick up.

### Adding the Sonar Pipe

Add a step like the following to the appropriate pipelines in your `bitbucket-pipelines.yml`.

```
- step:
    name: Run SonarQube
    script:
      - pipe: docker://atlassian/artifactory-sidekick:latest
      - source .artifactory/activate.sh
      - pipe: docker://docker.atl-paas.net/sox/mobuild/sonar-pipe:stable
        variables:
          DEFAULT_BRANCH: main
          SERVICE_FAILSAFE: "true"
          CHECK_QUALITY_GATES: "true"
```

Ensure that your build steps persist the necessary artifacts that SonarQube will need in order to properly introspect your code. For example, for JVM services the following artifacts might be set up:

```
- step:
    name: Build and test
    artifacts:
      - "**/*.sd.yml"
      - "target/classes/**"
      - "target/test-classes/**"
      - "target/surefire-reports/**"
      - "target/failsafe-reports/**"
      - "target/site/**"
```
