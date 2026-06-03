# Qlever Learnings

## Resolved Issues
- Create this file for *qlever ui* to work

```bash
~$ cat /etc/docker/daemon.json
{
  "proxies": {
    "http-proxy": "http://proxy-dev.spk-berlin.de:3128",
    "https-proxy": "http://proxy-dev.spk-berlin.de:3128"
  }
}
```

- If the DBs are big, change the limit of number of files system can create using: 

```bash
ulimit -n 1000000 # allows the system to create 1million files
ulimit -n # verify it, generally it is set to 1024
```