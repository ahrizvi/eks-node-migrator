from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import subprocess
import time
from .logger import logger
from eksmigrator.config import app_config

def ensure_config_loaded():

    kube_config = os.getenv('KUBECONFIG')
    if kube_config and os.path.isfile(kube_config):
        try:
            config.load_kube_config(context=app_config['K8S_CONTEXT'])
        except config.ConfigException:
            raise Exception("Could not configure kubernetes python client")
    else:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config(context=app_config['K8S_CONTEXT'])
            except config.ConfigException:
                raise Exception("Could not configure kubernetes python client")

    proxy_url = os.getenv('HTTPS_PROXY', os.getenv('HTTP_PROXY', None))
    if proxy_url and not app_config['K8S_PROXY_BYPASS']:
        logger.info(f"Setting proxy: {proxy_url}")
        client.Configuration._default.proxy = proxy_url

def cordon_node(node_name):
    """
    Cordon a kubernetes node to avoid new pods being scheduled on it
    """

    ensure_config_loaded()

    # create an instance of the API class
    k8s_api = client.CoreV1Api()
    logger.info("Cordoning k8s node {}...".format(node_name))
    try:
        api_call_body = client.V1Node(spec=client.V1NodeSpec(unschedulable=True))
        if not app_config['DRY_RUN']:
            k8s_api.patch_node(node_name, api_call_body)
        else:
            k8s_api.patch_node(node_name, api_call_body, dry_run=True)
        logger.info("Node cordoned")
    except ApiException as e:
        logger.info("Exception when calling CoreV1Api->patch_node: {}".format(e))


def drain_node(node_name, timeout_s):
    """
    Executes kubectl commands to drain the node. We are not using the api
    because the draining functionality is done client side and to
    replicate the same functionality here would be too time consuming
    """
    kubectl_args = [
        'kubectl', 'drain', node_name,
        '--ignore-daemonsets',
        '--delete-emptydir-data'
    ]

    kubectl_args += app_config['EXTRA_DRAIN_ARGS']

    if app_config['DRY_RUN'] is True:
        kubectl_args += ['--dry-run']

    logger.info('Draining worker node with {}...'.format(
        ' '.join(kubectl_args)))
    process = subprocess.Popen(
        kubectl_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    timeout = timeout_s
    mustend = time.time() + timeout

    while True and time.time() < mustend:
        output = process.stdout.readline()
        error = process.stderr.readline()
        if process.poll() is not None and output == '':
            break
        if output:
            print(output.strip())
        if error:
            print(error.strip())

    #print("Node could not be drained properly, Exiting...")
    else:
        print(error)

    #retval = process.poll()
    rc = process.returncode

    # If process.returncode is non-zero, raise a CalledProcessError.
    if rc != 0:
        # print(error)
        raise Exception("Node can not be drained properly. Exiting")


def get_bad_state_pods():

    try:
        config.load_kube_config()
    except config.ConfigException:
        raise Exception("Could not configure kubernetes python client")

    v1 = client.CoreV1Api()

    api_response = v1.list_pod_for_all_namespaces(watch=False)

    pods_in_bad_state = []

    for item in api_response.items:
        if item.status.phase != "Running":
            pod_name = item.metadata.name
            pod_state = item.status.phase

            badPodState_dict = {}

            badPodState_dict["pod_name"] = pod_name
            badPodState_dict["pod_state"] = pod_state

            pods_in_bad_state.append(badPodState_dict)

    return len(pods_in_bad_state)
