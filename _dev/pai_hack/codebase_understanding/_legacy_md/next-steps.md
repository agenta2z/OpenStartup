# Gradle
- This is a normal Gradle project. Just load it in your IDE. Run 'bin/run-once/configure-gradle.sh' to configure Gradle initially.

# Renovate
- commit and push the newly generated renovate.json5 file to your repository's default branch (main)

# Micros Spring Boot
- If you are using a single application.yml file to manage different profiles, the template has split them into separate files. Please verify the changes.

# Continuous Chaos
- Redeploy your service to enable the Continuous Chaos resource
- Continuous Chaos replaces Faila. If your Service Descriptor has a Faila resource, you should be able to remove it.
- [More information on Continuous Chaos](https://hello.atlassian.net/wiki/x/WeoCvQ)

# Nebulae
- Ensure you have Docker running
- Ensure you have Nebulae installed:
        ```shell
        bin/run-once/install-nebulae.sh
        ```
- Start Nebulae using `atlas nebulae start`

# Spinnaker Deployments
- Refer to the readme at docs/spinnaker.md