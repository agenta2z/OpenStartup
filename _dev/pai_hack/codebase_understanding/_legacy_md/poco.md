## Poco

[Poco](https://developer.atlassian.com/platform/poco/) enables you to create an authorization policy for your service in a declarative way. For info, on how this works see [DAC docs](https://developer.atlassian.com/platform/poco/policies/).

### Installation

Make sure you have the Poco CLI installed following the instructions [here](https://developer.atlassian.com/platform/poco/cli/installation/).

### Authoring

Your policy is contained within the `src/main/resources/policies/service` directory. The `policy.json` file declares what type of requests should be allowed to which endpoints, and by default any other requests are denied. You can find more documentation on writing policies [here](https://developer.atlassian.com/platform/poco/policies/kinds/slauth/).

**You should update this policy example to reflect the endpoints and authorization model that your service needs. The provided policy serves simply as a skeleton for you to write your own.**

### Testing

Once your policy has been written, you can write tests to assert that it behaves in the way you intend. The `tests.json` contains a few basic tests, but these will change as your policy gets updated. You can find more docs on testing your policy [here](https://developer.atlassian.com/platform/poco/policies/workflow/testing/).

You can run tests for your policy via:

```
cd src/main/resources/policies
atlas poco bundle test -b service -t tests.json
```

### Publishing

Once your policy behaves as intended, you can publish the policy following the steps on [uploading](https://developer.atlassian.com/platform/poco/policies/workflow/uploading/) then [tagging](https://developer.atlassian.com/platform/poco/policies/workflow/tagging/).

### Monitoring

Poco provides metrics and dashboards for you to glean insights from decision logs, monitor policy updates, how long Poco takes to authorize the request, and more. You can find more on info on that [here](https://developer.atlassian.com/platform/poco/policies/workflow/monitoring/).
