# Security Best Practices - Experimental Service

Check out the below best practices from [Product Security](go/prodsec).

## Authentication & Authorization

- Ensure your application has appropriate authentication & authorization.
  > We recommend using **SLAuth & Poco**. Guide: [Configure your Spring Boot service to use with SLAuth and Poco](https://hello.atlassian.net/wiki/spaces/MICROS/pages/904339179)

- Ensure your service is minting & handling tokens securely.
  > We recommend using **ASAP**. 
    Guide:  [ASAP Authentication - Java](https://bitbucket.org/atlassian/asap-java/src/main/)


## Secure Data Processing

 - Establish appropriate encryption of sensitive data during transmission & at rest. 
   > We recommend encryption of sensitive data & key management using **Cryptor**. Guide: [Encryption of stored data - Cryptor](https://hello.atlassian.net/wiki/spaces/PRODSEC/pages/2369083257/Encryption+of+stored+data#Cryptor)
    
   > For encryption of data during transmission, Guide:  [Transport Layer Security Guidance](https://hello.atlassian.net/wiki/spaces/PRODSEC/pages/2728100027/Insufficient+Transport+Layer+Security+TLS#Client-Side-Transport-Layer-Security-(TLS))
    

## Logging

- Assure appropriate logging is enabled for your service. 
   > Check out the [do’s](https://hello.atlassian.net/wiki/spaces/PMP/pages/139161662/Standard+-+Logging#Standard) and [don’ts](https://hello.atlassian.net/wiki/spaces/PMP/pages/139161662/Standard+-+Logging#Don't-log-Customer-Content) for logging.

   > Recommended [formats](https://hello.atlassian.net/wiki/spaces/PMP/pages/1384616197/Standard+-+Log+Types+Events+and+Records#Information-Logging-(Milestone)) & examples (expand boxes for each). 

## Clean-up

 - Confirm that your stale/unused services are not lingering around. 

    > Guide: [Deleting a Micros service](https://hello.atlassian.net/wiki/spaces/MICROS/pages/257721993)