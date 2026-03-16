# sing_box_local_route_analysis
Sing Box route analysis

You ned to activate Clash API !

```
"experimental": {
    "clash_api": {
      "external_controller": "127.0.0.1:9090",
      "secret": "yoour_passsword"
    }
  }
```

# Только в stdout
```
python3 singbox_connections_log.py --api http://127.0.0.1:9090 --secret YOUR_SECRET
```
# В файл + stdout
```
python3 singbox_connections_log.py --secret YOUR_SECRET --log-file /var/log/singbox_connections.log
```
# Через env
```
SINGBOX_SECRET=YOUR_SECRET python3 singbox_connections_log.py
```
