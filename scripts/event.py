from kop.provider.events import Events
from kop.provider.client import KbsAuthLoader



client = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/34f789a7-2458-412d-8416-2a74ff26ae2c")
event = Events(client.api_client, "nginx-deployment-565cb86996-8g4mk", "default")
event.watch_events()