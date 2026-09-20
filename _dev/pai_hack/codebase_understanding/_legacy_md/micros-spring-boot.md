# Micros Spring Boot

- Micros Spring Boot is a framework built on top of Spring Boot used for creating standalone,
  production grade applications.
- Learn more about its features [here](https://developer.atlassian.com/platform/framework/micros-spring-boot/).
- The template does the micros spring boot setup for you by adding the MSB bom dependency to your maven or gradle project.
- It also adds application properties to your project.
- Micros Spring Boot will automatically use pretty printed logging when running locally, but will
  activate JSON based logging when deployed to Micros.

## Understanding the configuration

- The service configuration files are `src/main/resources/application-<profile>.yml`,
  following Spring Boot's standard for [externalized configuration](https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/#features.external-config).
- If no profile is active (or a configuration property is not available for a given profile),
  configuration values will be read from the file `application.yml` (without a profile suffix).
- Micros Spring Boot will automatically detect the Micros environment you are deployed to
  and activate the appropriate profiles. It activates both an environment specific profile (e.g. `stg-west`, `prod-west`),
  and a logical environment (e.g. `dev`, `staging`, `prod`) so configuration can be shared for a logical environment.
- All properties defined in the `application-<profile>.yml` files can also be overridden by system properties or
  environment variables. For more information read the [Spring Boot documentation](https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/#features.external-config).
