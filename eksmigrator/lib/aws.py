import boto3
from .logger import logger
from eksmigrator.config import app_config

aws_reg = app_config['AWS_DEFAULT_REGION']

# Set AWS Profile and region for script execution
#boto3.setup_default_session(profile_name="kube-dev-sre")
client = boto3.client('autoscaling', region_name=aws_reg)
ec2_client = boto3.client('ec2', region_name=aws_reg)


def get_asgs(cluster_name, nodegroup):
    """
    Queries AWS and returns all ASG's matching the cluster-name-ng format
    """
    asg_filter_tag = cluster_name[:-4]+"-asg-"+nodegroup

    #logging.info('Describing autoscaling groups...')
    paginator = client.get_paginator('describe_auto_scaling_groups')
    page_iterator = paginator.paginate(
        PaginationConfig={'PageSize': 100}
    )

    asg_query = "AutoScalingGroups[] | [?contains(AutoScalingGroupName, `{}`)]".format(
        asg_filter_tag)

    # filter for only asgs with kube cluster tags
    filtered_asgs = page_iterator.search(asg_query)
    #filtered_asgs = page_iterator

    return filtered_asgs


def get_ec2_pvt_dns(instance_id):
    try:
        client = boto3.client('ec2', region_name='eu-west-1')
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running'],
                },
                {
                    'Name': 'instance-id',
                    'Values': [instance_id],
                }

            ]
        )

        ec2pvtDNS = []
        for r in response['Reservations']:

            for i in r['Instances']:
                ec2Info_dic = {}
                instance_id = i.get('InstanceId')
                private_ip = i.get('PrivateIpAddress')
                private_dns = i.get('PrivateDnsName')

                ec2Info_dic["instance_id"] = instance_id
                ec2Info_dic["private_ip"] = private_ip
                ec2Info_dic["private_dns"] = private_dns

                ec2pvtDNS.append(ec2Info_dic)
        return ec2pvtDNS
    except:
        raise
