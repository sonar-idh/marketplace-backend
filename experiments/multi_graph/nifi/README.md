# Nifi
## Setup
```bash
sudo apt update && sudo apt install -y openjdk-21-jdk
wget https://dlcdn.apache.org/nifi/2.9.0/nifi-2.9.0-bin.zip
wget https://downloads.apache.org/nifi/2.9.0/nifi-2.9.0-bin.zip.asc
wget https://downloads.apache.org/nifi/2.9.0/nifi-2.9.0-bin.zip.sha512

# verify keys
if echo "$(cat nifi-2.9.0-bin.zip.sha512) nifi-2.9.0-bin.zip" | sha512sum -c - &> /dev/null; then
    echo "Hash match verified! Unzipping file..."
    unzip nifi-2.9.0-bin.zip
else
    echo "ERROR: Hash mismatch! The download might be corrupted." >&2
    exit 1
fi

# change the conf/properties manually
# Network properties for NIFI
# hostname -I
#nifi.web.https.host=10.46.3.135
#nifi.web.https.port=8443

# Access control properties
#nifi.web.proxy.host=10.46.3.135:8443

# Get the first IP address from hostname -I
SERVER_IP=$(hostname -I | awk '{print $1}')

# 2. Replace the lines dynamically in nifi.properties
sed -i "s|^.*nifi.web.https.host=.*|#nifi.web.https.host=${SERVER_IP}|" conf/nifi.properties
sed -i "s|^.*nifi.web.https.port=.*|#nifi.web.https.port=8443|" conf/nifi.properties
sed -i "s|^.*nifi.web.proxy.host=.*|#nifi.web.proxy.host=${SERVER_IP}:8443|" conf/nifi.properties

# 3. Verify the changes
grep -E "nifi.web.https.host|nifi.web.https.port|nifi.web.proxy.host" conf/nifi.properties

# Run Nifi
./nifi-2.9.0/bin/nifi.sh start

```

```bash

```