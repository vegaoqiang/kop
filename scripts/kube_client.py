from kop.provider.client import KbsEndpoint

k = KbsEndpoint(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/34f789a7-2458-412d-8416-2a74ff26ae2c")
# dp = k.list_deployments()
# for d in dp.items:
#     if d.metadata.name == "coredns":
#         print(d)

pods = k.list_pods()
for p in pods.items:
    if p.metadata.name == "nginx-deployment-8c47f7c45-jmgwf":
        print(p)