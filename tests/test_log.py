from kop.components.Log import LogController, PodLogs
from kop.kube.client import KbsAuthLoader
from textual.app import App


k = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
Log = PodLogs(k.api_client, "nginx-deployment-565cb86996-8g4mk", "default")

log_controller = LogController(pod_logs=Log)
log_controller.start()

for line in log_controller.poll_logs():
    print(line)


