## SLAuth Authentication

This service includes base configuration for authentication using the SLAuth sidecar.
You can find docs for the sidecar [on DAC](https://developer.atlassian.com/platform/slauth/).

You can read about the security features [here](https://developer.atlassian.com/platform/framework/micros-spring-boot/security/slauth/).

Using SLAuth via Service Proxy involves configuration that looks different than using SLAuth as a service sidecar. Make sure you refer to the appropriate section in the docs for [Service Proxy usage](https://developer.atlassian.com/platform/slauth/serviceproxy/configuration/)(recommended) or for [Service Sidecar usage](https://developer.atlassian.com/platform/slauth/sidecar/configuration/).

### Local development

Once your service is running in Micros, the SLAuth sidecar will handle authentication of all requests. You can configure
what type of requests (e.g. ASAP, SLAuthtoken, etc.) by configuring the [sidecar plugins](https://developer.atlassian.com/platform/slauth/sidecar/plugins/).

For local development, your service will expect `X-Slauth-*` headers, which indicate a request was authenticated and authorized by SLAuth. If you are connecting directly to your service, for example when running directly from an IDE, you can mock these headers via:

```shell
curl localhost:8080/api/greetings/user \
  -H X-Slauth-Subject:you \
  -H X-Slauth-Mechanism:slauthtoken \
  -H X-Slauth-Principal:slauth \
  -H X-Slauth-Authorization:true
```

or consider using [Nebulae](https://developer.atlassian.com/platform/nebulae/), which will automatically create those headers for you.
