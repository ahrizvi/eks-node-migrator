#!/usr/bin/env python
import sys
import argparse
import time
import shutil

from .config import app_config
from .lib.logger import logger
from .lib.aws import get_asgs, get_ec2_pvt_dns
from .lib.k8s import drain_node, cordon_node, get_bad_state_pods
from .lib.exceptions import NodeMigratorException


def get_k8s_nodes(filtered_asgs):

   # instance_ids = get_asgs(cluster_name,nodegroup)

    k8s_nodes_list = []

    for asg in filtered_asgs:
        instance_pvt_dns = get_ec2_pvt_dns(asg["Instances"][0]["InstanceId"])[
            0]["private_dns"]

        k8s_nodes_list.append(instance_pvt_dns)

    return k8s_nodes_list


def update_asgs_cordon(node):
    try:
        # get the k8s node name instead of instance id
        cordon_node(node)

    except Exception as cordon_exception:
        logger.error(
            f"Encountered an error when cordoning node {node}")
        logger.error(cordon_exception)
        exit(1)


def update_asgs_drain(node, timeout_s):
    # catch any failures so we can resume aws autoscaling
    try:
        # get the k8s node name instead of instance id
        drain_node(node, timeout_s)

        between_nodes_wait = app_config['BETWEEN_NODES_WAIT']
        if between_nodes_wait != 0:
            logger.info(
                f'Waiting for {between_nodes_wait} seconds before continuing...')
            time.sleep(between_nodes_wait)

    except Exception as drain_exception:
        logger.info(drain_exception)
        raise NodeMigratorException(
            "Rolling drain operation on Nodegroup has failed")


# wait for something to be ready
def pod_health_check(init_state):
    current_bad_pods = get_bad_state_pods()
    if current_bad_pods >= init_state:
        logger.info(
            "Current PODs not in Running state before next drain operations:  " + str(current_bad_pods))
        return True
    return False


def wait_until(health_chk_func, timeout, period=0.25, *args, **kwargs):

    mustend = time.time() + timeout

    while time.time() < mustend:
        if health_chk_func == True:
            return True
        time.sleep(period)

    return False


def main(args=None):
    parser = argparse.ArgumentParser(
        description='The tool to perform eks node drain/cordon ops')
    parser.add_argument('--cluster_name', '-c', required=True,
                        help='the cluster name to perform drain or cordon operation on')
    parser.add_argument('--nodegroup', '-ng', required=True,
                        help='the nodegroup name to perform drain or cordonupdate on')
    parser.add_argument('--action', '-a', required=True,
                        help='the action to be performed i.e. drain or cordon')

    args = parser.parse_args(args)

    # check kubectl is installed

    kctl = shutil.which('kubectl')
    if not kctl:
        logger.info('kubectl is required to be installed before proceeding')
        quit(1)

    filtered_asgs = get_asgs(args.cluster_name, args.nodegroup)
    bad_state_pods_init = get_bad_state_pods()
    logger.info("PODs not in Running state before drain/cordon operations:  " +
                str(bad_state_pods_init))

    k8s_nodes_list = get_k8s_nodes(filtered_asgs)

    # perform real update

    if args.action == "cordon" and int(len(k8s_nodes_list)) != 0:

        try:
            logger.info(args.action + " operation will be peformed on " +
                        str(len(k8s_nodes_list)) + " nodes")

            for node in k8s_nodes_list:
                update_asgs_cordon(node)
            logger.info(
                '*** All nodes in provided Nodegroup have been cordoned ! ***')

        except Exception as e:
            logger.error(e)
            logger.error(
                '*** EKS node cordon operation of provided Nodegroup has failed. Exiting ***')
            sys.exit(1)

    elif args.action == "drain" and int(len(k8s_nodes_list)) != 0:

        try:
            logger.info(args.action + " operation will be peformed on " +
                        str(len(k8s_nodes_list)) + " nodes")
            for node in k8s_nodes_list:
                logger.info(
                    '*** Checking PODs health status before continuing with drain operations ! ***')

                wait_until_resp = wait_until(
                    pod_health_check(bad_state_pods_init), 30)

                if wait_until_resp == True:
                    update_asgs_drain(node, 90)
                    print(
                        "PODs in pending state after current node drain =   " + str(get_bad_state_pods()))

                else:
                    "Node drain operation can not be continued as PODs from already drained nodes have not transitioned to running state for longer time"

            logger.info(
                '*** All nodes in provided Nodegroup and cluster have been drained ! ***')

        except Exception as e:
            logger.error(e)
            logger.error(
                '*** EKS node drain operation has failed. Exiting ***')
            sys.exit(1)

    else:
        try:
            if int(len(k8s_nodes_list)) == 0:
                raise Exception(
                    "The cluster name or Nodegroup name is incorrect")

        except Exception as e:
            logger.error(e)
            sys.exit(1)

        try:
            if args.action != 'drain' or args.action != 'cordon':
                raise Exception(
                    "Please choose a valid operation to be performed on cluster Nodegroup")

        except Exception as e:
            logger.error(e)
            sys.exit(1)

