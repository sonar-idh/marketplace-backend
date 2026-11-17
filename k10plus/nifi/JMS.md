# JMS Setup in NiFi and Fedora Commons

## TL;DR
- **SoNAR JMS Test**: NiFi Pipeline that receives messages from Fedora Commons when there is Create|Update|Delete to the resources.
- **Message Delivery Mode and Stroage** : Topic with Durable Subscription. aka (publish/subscribe with Persistence)

*Note: Persistent Queue is possible too (TBD).*

To set up communication between NiFi and Fedora Commons, the following steps are needed:

## Fedora Checklist
- JMS (uses Apache ActiveMQ) must be enabled in Fedora Commons.
- By default, ActiveMQ uses **OpenWire** protocol on TCP port 61616.
- **Persistence**: KahaDB is ActiveMQ's default message store. Only persistent messages are kept, and a durable subscription must be set in NiFi so that events are not lost while NiFi is offline.
- **Security**: By default, the broker listens on 0.0.0.0 without authentication. Restrict access and/or enable authentication.

```bash
# To test whether JMS is reachable (run from the NiFi host)
nc -zv <serverIP> <port>

# To check whether the events are written to kahaDB
sudo strings -a  <kahadb-dir>/db-*.log | grep -i -E 'activitystreams|fedora.info|"type"|Create|Update|Delete' | head

# Check whether the durable subscription was registered
# Subscription Name from consumeJMS
sudo strings -a <kahadb-dir>/db-*.log | grep -i -E '<subscription name>'
```

## NiFi Checklist
- **ConsumeJMS** processor
- **JMSConnectionFactoryProvider** controller service
- **libs** installation/copy

```bash
# Copy required libraries from Fedora Server to NiFi Server
scp <user>@<fedoraserverip>:<tomcat-webapps>/<fedora-context>/WEB-INF/lib/{activemq-client-6.2.1,activemq-broker-6.2.1,activemq-openwire-legacy-6.2.1,hawtbuf-1.11,jakarta.jms-api-3.1.0}.jar /opt/nifi/jms-libs/

# read access
chmod -R a+rX /opt/nifi/jms-libs
```

## Other Details
- To discover the destination name, temporarily set ConsumeJMS Destination Name to `>` (wildcard). Create a change in Fedora Commons and check *jms_destination* in the new provenance event.

### Configuration
All processor and controller-service settings are in `SoNAR__JMS_Test.template.json` (placeholders only).

After import, set `fedora_jms_uri`, `fedora_url`, `fedora_user`, `fedora_password` in the parameter context.

### Important
- **Jars**: NiFi 2.x needs the Jakarta client (ActiveMQ 6.x). The 5.x jars from older Fedora deployments do not work. "JMS Client Libraries" takes a directory path, not artifact names.
- **Durable subscription** is identified by *Client ID + Subscription Name* and is stored on the broker. It exists only after NiFi has connected once. Changing either value creates a new subscription.
- **Moving the flow** to another NiFi with the same Client ID and Subscription Name resumes the backlog. Only one connection per Client ID is allowed.
- **Delivery is at-least-once**: downstream steps must be idempotent.
- **Security**: port 61616 is unauthenticated; restrict it to the NiFi host (firewall/security group).
- **Disk**: a full KahaDB store can block Fedora writes.
