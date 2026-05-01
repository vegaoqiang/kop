# Tutorial

## Add Kubernetes CLuster

After starting kop, it reads the ~/.kube/config file by default.

> ~/.kube/config is the default configuration file for Kubernetes (often called the kubeconfig file). It contains information about connecting to and authenticating the Kubernetes cluster (such as API server addresses, certificates, and tokens) and context information. The kubectl command-line tool uses this file by default to communicate with the cluster and manages access information for multiple clusters, users, and namespaces.


If the host running kop does not have Kubernetes (connecting to a remote Kubernetes cluster over the network). After starting kop, you will see relevant prompts.

![startup_without_cluster](images/tutorial/startup_without_cluster.png)

At this point, you can open the `Add Cluster` view by clicking the `[Add]` button with the mouse or pressing `a` on the keyboard.

![add_new_cluster](images/tutorial/add_new_cluster.png)

Then paste the contents of your kubeconfig file into the `Paste Your Cluster Config` area. Then paste the contents of your kubeconfig file into the content area, and then click the `[Save]` button or press `'ctrl+s'` to save.

### Multiple clusters exist in kubeconfig
If a kubeconfig file contains multiple cluster configurations, Kop will split the kubeconfig according to the cluster dimension when importing it. After successful import, multiple clusters will be imported into the Kop cluster view.


## Sync kubeconfig
kop supports selecting the kubeconfig file for synchronous cluster configuration. It also supports directory synchronization, allowing you to place multiple kubeconfig files in the same directory. kop will then synchronize all valid kubeconfig files in that directory.

In the startup view, press the `[Sync]` button or the `'s' ` key to enter the kubeconfig file selection view.


## Edit Cluster
In the `Startup` view, after selecting a cluster, you can edit the cluster by clicking the `[Edit]` button or pressing the `'e'` key.


## Delete Cluster
In the `Startup` view, after selecting a cluster, you can delete the selected cluster by clicking the `[Delete]` button or pressing the `'d'` key.

## Connect Cluster
In the `Startup` view, after selecting the target cluster, connect to the cluster by clicking the `[Connect]` button or pressing the `'c'` key. Once the connection is successful, kop will enter the cluster resource view.

>When starting kop, specify the cluster configuration file using `--kubeconfig /path/to/kubeconfig`. kop will then use this file to directly access the Kubernetes resource view.
