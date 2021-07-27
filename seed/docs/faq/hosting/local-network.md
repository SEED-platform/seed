---
question: Can the web interface of a self-hosted SEED instance be accessed via a local network, or is internet access required? Can access via local internet be disabled?
tags: []
---
Access via public internet would be a function of the self-hosted instance's network configuration. If SEED is hosted on Amazon Web Services, for example, the host can deny access based on CIDR blocks (IP address ranges) in the Amazon Web Services Console. If the application is hosted on user-owned infrastructure, a local firewall can prevent external access. Note that internal access in both cases would still be available (i.e., the web interface would be accessible).
