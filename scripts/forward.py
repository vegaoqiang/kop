import time
from kop.provider.client import KbsAuthLoader
from kop.provider.forward import PodPortForward,PodPortForwardManager, PortForwardSpec


client = KbsAuthLoader(config_file="/Users/gaoxiang/Library/Application Support/OpenLens/kubeconfigs/34f789a7-2458-412d-8416-2a74ff26ae2c", context="default")
mgr = PodPortForwardManager()

mgr.add_many(
    api_client=client.api_client,
    specs=[
        PortForwardSpec(pod_name="nginx-deployment-8c47f7c45-nrj5s", namespace="default", local_port=18080, remote_port=80),
        # PortForwardSpec(pod_name="pod-b", namespace="default", local_port=15432, remote_port=5432),
    ],
)

time.sleep(30)
# ...运行期间可轮询异常
# errors = mgr.poll_events(timeout=0)
# # 停止全部
# mgr.stop_all(remove=True)


# pf = PodPortForward(api_client=client.api_client, pod_name="nginx-deployment-8c47f7c45-nrj5s", namespace="default", local_port=18081, remote_port=80)
# pf.start()
