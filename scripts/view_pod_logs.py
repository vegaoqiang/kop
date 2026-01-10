from kop.provider.logs import LogController, PodLogs
from kop.provider.client import KbsAuthLoader
k = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
Log = PodLogs(k.api_client, "nginx-deployment-565cb86996-8g4mk", "default")
log_contaller = LogController(pod_logs=Log)

log_contaller.start()

try:
    while True:
        for line in log_contaller.poll_logs():
            print(line)
except KeyboardInterrupt:
    log_contaller.stop()