from kop.kube.client import KbsEndpoint

k = KbsEndpoint(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/196f5cce-07d5-4ac1-b1f8-61b14bc9bb72")
dp = k.list_deployments()
for d in dp.items:
    if d.metadata.name == "nginx-deployment":
        print(d)