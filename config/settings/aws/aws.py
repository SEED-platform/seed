"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import boto.elasticache
import boto.cloudformation
import boto.ec2
import boto.exception
import os

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

try:
    ec2 = boto.ec2.connect_to_region(AWS_REGION)
    elasticache = boto.elasticache.connect_to_region(AWS_REGION)
    cloudformation = boto.cloudformation.connect_to_region(AWS_REGION)
except boto.exception.NoAuthHandlerFound:
    print 'Looks like we are not on an AWS stack this module will not function'


def get_stack_outputs():
    if not AWS_REGION or 'STACK_NAME' not in os.environ:
        return {}
    return {
        output.key: output.value for output in (
            cloudformation.describe_stacks(os.environ['STACK_NAME'])[0].outputs
        )
    }


def get_cache_endpoint():
    outputs = get_stack_outputs()
    if not outputs or 'CacheClusterID' not in outputs:
        return None
    cluster = elasticache.describe_cache_clusters(
        outputs['CacheClusterID'], show_cache_node_info=True
    )
    return (
        cluster['DescribeCacheClustersResponse']['DescribeCacheClustersResult']
        ['CacheClusters'][0]['CacheNodes'][0]['Endpoint']
    )

if __name__ == '__main__':
    print get_cache_endpoint()['Address']
