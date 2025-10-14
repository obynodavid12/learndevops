#!/usr/bin/env python
"""
Enhanced AWS Subnet Usage and Resource Discovery Script
--------------------------------------------------------
Finds IP address usage in an AWS Subnet and identifies all related components:
- EC2 instances
- ENIs
- Auto Scaling Groups
- Classic/ALB/NLB load balancers
- EKS Nodegroups
- Tags associated with each resource (when available)

Requires:
  boto3
  netaddr

Usage:
  python aws_subnet_ip_usage.py <subnet-id or subnet-cidr> [-v]

Author: Adapted from Jason Antman (2018)
Enhanced by: ChatGPT (2025)
"""

import sys
import argparse
import logging
import re
import boto3
from botocore.exceptions import ClientError
from netaddr import IPNetwork

FORMAT = "[%(levelname)s %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger(__name__)

ELB_MAX_IPS = 8
ENI_ELB_RE = re.compile(r'^eni-[a-f0-9]+ / ELB (.+)$')


class AWSIPUsage:
    """Find AWS IP and resource usage by subnet"""

    def __init__(self):
        """Connect to AWS API"""
        logger.debug("Connecting to AWS API")
        self.ec2 = boto3.client('ec2')
        self.ec2_res = boto3.resource('ec2')
        self.autoscaling = boto3.client('autoscaling')
        self.elbv2 = boto3.client('elbv2')
        self.eks = boto3.client('eks')
        logger.info("Connected to AWS API")

    def show_subnet_usage(self, query):
        """Main entry point"""
        subnet = self._find_subnet(query)
        if subnet is None:
            logger.error("No matching subnets found. Check your AWS credentials/account.")
            sys.exit(1)

        print("\n=== SUBNET DETAILS ===")
        print(f"Subnet: {subnet['SubnetId']} | CIDR: {subnet['CidrBlock']} | "
              f"AZ: {subnet['AvailabilityZone']} | VPC: {subnet.get('VpcId', '')} | "
              f"{subnet['AvailableIpAddressCount']} IPs available")

        avail_ips = int(subnet['AvailableIpAddressCount'])
        ips = self._ips_for_subnet(subnet['CidrBlock'])
        used_ips = {}

        eni_ips = self._find_used_eni(subnet['SubnetId'])
        used_ips.update(eni_ips)

        ec2_ips = self._find_used_ec2_instances(subnet['SubnetId'])
        used_ips.update(ec2_ips)

        print(f"\n=== IP UTILIZATION ===")
        print(f"{len(used_ips)} IPs used out of {len(ips)} total in {subnet['CidrBlock']}")

        elb_count, elb_curr, elb_max = self._handle_elbs(used_ips, subnet['SubnetId'])
        print(f"Found {elb_count} ELB(s) using {elb_curr} IPs; Max possible: {elb_max}")

        asg_count, asg_curr, asg_max = self._handle_asgs(used_ips, subnet['SubnetId'], ec2_ips)
        print(f"Found {asg_count} ASG(s) with {asg_curr} instances; Max capacity: {asg_max}")

        # New: NLBs
        self._handle_nlbs(subnet['SubnetId'])

        # New: EKS Nodegroups
        self._handle_eks_nodegroups(subnet['SubnetId'])

        if len(used_ips) != (len(ips) - avail_ips):
            print("⚠️  WARNING: IP counts differ from AWS API. Other services may be using IPs.")
        print(f"\nSubnet has {len(ips)} usable IPs, {len(used_ips)} in use. "
              f"Theoretical max with all ELBs/ASGs scaled: {len(used_ips) + elb_max + asg_max}\n")

    # -------------------- RESOURCE HANDLERS --------------------

    def _handle_elbs(self, ips, subnet_id):
        """Handle Classic/ALB ELBs"""
        curr_ips = 0
        max_ips = 0
        elbnames = set()
        for ip, desc in ips.items():
            m = ENI_ELB_RE.match(desc)
            if m:
                elbnames.add(m.group(1))
        for elbname in elbnames:
            elb_enis = list(self.ec2_res.network_interfaces.filter(
                Filters=[{'Name': 'description', 'Values': [f'ELB {elbname}']},
                         {'Name': 'subnet-id', 'Values': [subnet_id]}]))
            curr_ips += len(elb_enis)
            max_ips += ELB_MAX_IPS
        return len(elbnames), curr_ips, max_ips

    def _handle_asgs(self, ips, subnet_id, ec2_ip_to_id):
        """Handle ASGs in subnet"""
        curr_ips = 0
        max_ips = 0
        count = 0
        paginator = self.autoscaling.get_paginator('describe_auto_scaling_groups')
        for page in paginator.paginate():
            for asg in page['AutoScalingGroups']:
                subnets = asg['VPCZoneIdentifier'].split(',')
                if subnet_id not in subnets:
                    continue
                for inst in asg['Instances']:
                    if inst['InstanceId'] in ec2_ip_to_id.values():
                        curr_ips += 1
                max_ips += asg['MaxSize']
                count += 1
        return count, curr_ips, max_ips

    def _handle_nlbs(self, subnet_id):
        """Find Network Load Balancers (NLBs) in subnet"""
        nlb_list = []
        paginator = self.elbv2.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            for lb in page['LoadBalancers']:
                if lb['Type'] == 'network':
                    subnet_ids = [az['SubnetId'] for az in lb.get('AvailabilityZones', [])]
                    if subnet_id in subnet_ids:
                        tags = self._get_tags(lb['LoadBalancerArn'])
                        nlb_list.append({
                            'Name': lb['LoadBalancerName'],
                            'DNS': lb['DNSName'],
                            'State': lb['State']['Code'],
                            'ARN': lb['LoadBalancerArn'],
                            'Tags': tags
                        })
        print(f"\n=== NLBs in {subnet_id} ===")
        if not nlb_list:
            print("No NLBs found.")
        else:
            for nlb in nlb_list:
                print(f"  - {nlb['Name']} ({nlb['DNS']}) [{nlb['State']}]")
                if nlb['Tags']:
                    print(f"    Tags: { {t['Key']: t['Value'] for t in nlb['Tags']} }")

    def _handle_eks_nodegroups(self, subnet_id):
        """Find EKS Nodegroups using this subnet"""
        nodegroups_found = []
        clusters = self.eks.list_clusters().get('clusters', [])
        for cluster in clusters:
            ngs = self.eks.list_nodegroups(clusterName=cluster)['nodegroups']
            for ng in ngs:
                desc = self.eks.describe_nodegroup(clusterName=cluster, nodegroupName=ng)['nodegroup']
                subnets = desc.get('subnets', [])
                if subnet_id in subnets:
                    nodegroups_found.append({
                        'Cluster': cluster,
                        'NodeGroup': ng,
                        'InstanceTypes': desc.get('instanceTypes', []),
                        'Scaling': desc.get('scalingConfig', {}),
                        'Status': desc.get('status')
                    })
        print(f"\n=== EKS Nodegroups in {subnet_id} ===")
        if not nodegroups_found:
            print("No EKS Nodegroups found.")
        else:
            for ng in nodegroups_found:
                print(f"  - {ng['Cluster']}/{ng['NodeGroup']} [{ng['Status']}] {ng['InstanceTypes']}")
                print(f"    Scaling: {ng['Scaling']}")

    # -------------------- HELPERS --------------------

    def _find_used_eni(self, subnet_id):
        """Find ENIs in subnet"""
        res = {}
        for eni in self.ec2_res.network_interfaces.filter(
            Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}]):
            for ipaddr in eni.private_ip_addresses:
                res[ipaddr['PrivateIpAddress']] = f"{eni.id} / {eni.description}"
        return res

    def _find_used_ec2_instances(self, subnet_id):
        """Find EC2 instances in subnet"""
        res = {}
        paginator = self.ec2.get_paginator('describe_instances')
        for page in paginator.paginate(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}]):
            for r in page['Reservations']:
                for inst in r['Instances']:
                    ip = inst.get('PrivateIpAddress')
                    if ip:
                        res[ip] = inst['InstanceId']
        return res

    def _ips_for_subnet(self, cidr):
        """Return list of all IPs in subnet"""
        net = IPNetwork(cidr)
        return [str(x) for x in list(net[4:-1])]

    def _get_tags(self, arn_or_id):
        """Fetch tags for a resource"""
        try:
            if arn_or_id.startswith("arn:aws:elasticloadbalancing"):
                tags = self.elbv2.describe_tags(ResourceArns=[arn_or_id])
                return tags['TagDescriptions'][0]['Tags']
            else:
                tags = self.ec2.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [arn_or_id]}])
                return tags['Tags']
        except Exception as e:
            logger.debug(f"Could not get tags for {arn_or_id}: {e}")
            return []

    def _find_subnet(self, query):
        """Find subnet by ID or CIDR"""
        if re.match(r'^subnet-[a-fA-F0-9]+$', query):
            kwargs = {'SubnetIds': [query]}
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}', query):
            kwargs = {'Filters': [{'Name': 'cidrBlock', 'Values': [query]}]}
        else:
            sys.exit(f"ERROR: Invalid subnet identifier: {query}")
        subnets = self.ec2.describe_subnets(**kwargs)['Subnets']
        if not subnets:
            sys.exit(f"ERROR: No subnet found for {query}")
        if len(subnets) > 1:
            print("⚠️  Multiple subnets found, selecting first match.")
        return subnets[0]


def parse_args(argv):
    """Parse CLI args"""
    p = argparse.ArgumentParser(description="Find AWS IP usage and resources by subnet")
    p.add_argument("SUBNET_ID_OR_BLOCK", help="Subnet ID (e.g. subnet-abc123) or CIDR (e.g. 10.0.1.0/24)")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    finder = AWSIPUsage()
    finder.show_subnet_usage(args.SUBNET_ID_OR_BLOCK)




#cld

#!/usr/bin/env python
"""
Python script to find IP address usage in an AWS Subnet, and then estimate
usage with all resources scaled-out.

Currently calculates scale-out for:

* ASGs
* ELBs (Classic, Application, and Network Load Balancers)
* EKS Node Groups

Shows tags for NLBs and EKS instances.

Should work with python 2.7-3.6. Requires ``boto3`` and ``netaddr`` from pypi.

Enhanced to include NLB and EKS node group tag information.
"""

import sys
import argparse
import logging
import re

try:
    import boto3
except ImportError:
    raise SystemExit("This script requires boto3. Please 'pip install boto3'")
from botocore.exceptions import ClientError

try:
    from netaddr import IPNetwork
except ImportError:
    raise SystemExit("This script requires netaddr. Please 'pip install netaddr'")

FORMAT = "[%(levelname)s %(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger(__name__)


ELB_MAX_IPS = 8
ENI_ELB_RE = re.compile(r'^eni-[a-f0-9]+ / ELB (.+)$')
ENI_NLB_RE = re.compile(r'^ELB net/([^/]+)/.*$')
ENI_EKS_RE = re.compile(r'.*eks.*', re.IGNORECASE)


class AWSIPUsage:
    """Find AWS IP usage by subnet"""

    def __init__(self):
        """connect to AWS API"""
        logger.debug("Connecting to AWS API")
        self.ec2 = boto3.client('ec2')
        self.ec2_res = boto3.resource('ec2')
        self.autoscaling = boto3.client('autoscaling')
        self.elbv2 = boto3.client('elbv2')
        self.eks = boto3.client('eks')
        logger.info("Connected to AWS API")

    def show_subnet_usage(self, query, show_tags=False):
        """main entry point"""
        subnet = self._find_subnet(query)
        if subnet is None:
            logger.error(
                'No matching subnets found! (Are you authenticated to the '
                'right account?)'
            )
            raise SystemExit(1)
        print("Found matching subnet: %s (%s) %s %s (%s IPs available)" % (
                    subnet['SubnetId'],
                    subnet['CidrBlock'],
                    subnet['AvailabilityZone'],
                    subnet.get('VpcId', ''),
                    subnet['AvailableIpAddressCount']
        ))
        avail_ips = int(subnet['AvailableIpAddressCount'])
        ips = self._ips_for_subnet(subnet['CidrBlock'])
        logger.debug("Network has %d IPs", len(ips))
        used_ips = {}
        eni_ips = self._find_used_eni(
            subnet['SubnetId'], subnet['CidrBlock'], ips
        )
        used_ips.update(eni_ips)
        ec2_ips = self._find_used_ec2_instances(
            subnet['SubnetId'], subnet['CidrBlock'], ips, show_tags
        )
        used_ips.update(ec2_ips)
        print(
            "%d IP addresses used, out of %d total" % (len(used_ips), len(ips))
        )
        
        # Handle Classic and Application ELBs
        elb_count, elb_curr, elb_max = self._handle_elbs(
            used_ips, subnet['SubnetId']
        )
        print('Found %d Classic/ALBs currently using %d IPs; max IP usage is %d' % (
            elb_count, elb_curr, elb_max
        ))
        
        # Handle Network Load Balancers
        nlb_count, nlb_curr, nlb_max, nlb_details = self._handle_nlbs(
            used_ips, subnet['SubnetId'], show_tags
        )
        print('Found %d NLBs currently using %d IPs; max IP usage is %d' % (
            nlb_count, nlb_curr, nlb_max
        ))
        if show_tags and nlb_details:
            print("\nNetwork Load Balancer Details:")
            for nlb in nlb_details:
                print("  NLB: %s" % nlb['name'])
                print("    ARN: %s" % nlb['arn'])
                print("    IPs in subnet: %d" % nlb['ip_count'])
                if nlb['tags']:
                    print("    Tags:")
                    for key, value in nlb['tags'].items():
                        print("      %s: %s" % (key, value))
                else:
                    print("    Tags: None")
                print()
        
        # Handle ASGs
        asg_count, asg_curr, asg_max = self._handle_asgs(
            used_ips, subnet['SubnetId'], ec2_ips
        )
        print(
            'Found %d ASGs with %d total instances in the subnet. Maximum '
            'total instances: %s' % (asg_count, asg_curr, asg_max)
        )
        
        # Handle EKS
        eks_count, eks_details = self._handle_eks(
            subnet['SubnetId'], ec2_ips, show_tags
        )
        print('Found %d EKS-related instances in the subnet' % eks_count)
        if show_tags and eks_details:
            print("\nEKS Instance Details:")
            for cluster_name, instances in eks_details.items():
                print("  Cluster: %s" % cluster_name)
                for inst in instances:
                    print("    Instance: %s (IP: %s)" % (
                        inst['instance_id'], inst['ip']
                    ))
                    if inst['tags']:
                        print("      Tags:")
                        for key, value in inst['tags'].items():
                            print("        %s: %s" % (key, value))
                    else:
                        print("      Tags: None")
                print()
        
        if len(used_ips) != (len(ips) - avail_ips):
            print("WARNING: number of available IPs found does not match the "
                  "number reported by the API. Other IPs may be in use by "
                  "services not checked by this script!")
        total_max = len(used_ips) + elb_max + nlb_max + asg_max
        print('Subnet has %d usable IPs, %d IPs in use. Theoretical '
              'maximum with all ELBs, NLBs, and ASGs fully scaled: %d' % (
                  len(ips), len(used_ips), total_max
              )
        )

    def _handle_nlbs(self, ips, subnet_id, show_tags=False):
        """
        Figure out the current number, and maximum number, of IPs for
        Network Load Balancers in the subnet.

        :returns: number of NLBs in subnet, count of NLB IPs currently in use
          in subnet, count of maximum NLB IPs in subnet, list of NLB details
        :rtype: tuple
        """
        curr_ips = 0
        max_ips = 0
        nlb_arns = set()
        nlb_details = []
        
        # Find NLB ENIs
        for ip, desc in ips.items():
            m = ENI_NLB_RE.match(desc)
            if m is not None:
                nlb_name = m.group(1)
                logger.debug('IP %s is ENI for NLB "%s"', ip, nlb_name)
        
        # Get all NLBs
        try:
            paginator = self.elbv2.get_paginator('describe_load_balancers')
            for page in paginator.paginate():
                for lb in page['LoadBalancers']:
                    if lb['Type'] != 'network':
                        continue
                    
                    # Check if NLB uses this subnet
                    for az in lb.get('AvailabilityZones', []):
                        if az.get('SubnetId') == subnet_id:
                            nlb_arns.add(lb['LoadBalancerArn'])
                            
                            # Count IPs for this NLB in this subnet
                            nlb_ips = sum(
                                1 for ip, desc in ips.items()
                                if lb['LoadBalancerName'] in desc
                            )
                            curr_ips += nlb_ips if nlb_ips > 0 else 1
                            max_ips += ELB_MAX_IPS
                            
                            if show_tags:
                                # Get tags for this NLB
                                tags = {}
                                try:
                                    tag_response = self.elbv2.describe_tags(
                                        ResourceArns=[lb['LoadBalancerArn']]
                                    )
                                    for tag_desc in tag_response['TagDescriptions']:
                                        for tag in tag_desc.get('Tags', []):
                                            tags[tag['Key']] = tag['Value']
                                except ClientError as e:
                                    logger.warning(
                                        "Could not get tags for NLB %s: %s",
                                        lb['LoadBalancerName'], e
                                    )
                                
                                nlb_details.append({
                                    'name': lb['LoadBalancerName'],
                                    'arn': lb['LoadBalancerArn'],
                                    'ip_count': nlb_ips if nlb_ips > 0 else 1,
                                    'tags': tags
                                })
                            break
        except ClientError as e:
            logger.warning("Error querying NLBs: %s", e)
        
        return len(nlb_arns), curr_ips, max_ips, nlb_details

    def _handle_eks(self, subnet_id, ec2_ip_to_id, show_tags=False):
        """
        Find EKS instances in the subnet and their details.

        :returns: Count of EKS instances, dictionary of cluster details
        :rtype: tuple
        """
        eks_instances = {}
        eks_count = 0
        
        # Get all instance IDs in the subnet
        instance_ids = list(set(ec2_ip_to_id.values()))
        instance_ids = [
            iid.split('/')[0] for iid in instance_ids if iid.startswith('i-')
        ]
        
        if not instance_ids:
            return 0, {}
        
        # Get instance details including tags
        try:
            paginator = self.ec2.get_paginator('describe_instances')
            resp = paginator.paginate(InstanceIds=instance_ids)
            
            for r in resp:
                for reservation in r['Reservations']:
                    for inst in reservation['Instances']:
                        tags = {
                            tag['Key']: tag['Value']
                            for tag in inst.get('Tags', [])
                        }
                        
                        # Check if instance is part of EKS
                        cluster_name = None
                        if 'eks:cluster-name' in tags:
                            cluster_name = tags['eks:cluster-name']
                        elif 'kubernetes.io/cluster/' in str(tags):
                            for key in tags:
                                if key.startswith('kubernetes.io/cluster/'):
                                    cluster_name = key.split('/')[-1]
                                    break
                        
                        if cluster_name:
                            eks_count += 1
                            if cluster_name not in eks_instances:
                                eks_instances[cluster_name] = []
                            
                            instance_ip = inst.get('PrivateIpAddress', 'N/A')
                            eks_instances[cluster_name].append({
                                'instance_id': inst['InstanceId'],
                                'ip': instance_ip,
                                'tags': tags if show_tags else {}
                            })
        except ClientError as e:
            logger.warning("Error querying instance details: %s", e)
        
        return eks_count, eks_instances

    def _handle_elbs(self, ips, subnet_id):
        """
        Figure out the current number, and maximum number, of IPs for
        Classic/Application ELBs in the subnet.

        :returns: number of ELBs in subnet, count of ELB IPs currently in use
          in subnet, count of maximum ELB IPs in subnet
        :rtype: tuple
        """
        curr_ips = 0
        max_ips = 0
        elbnames = set()
        for ip, desc in ips.items():
            m = ENI_ELB_RE.match(desc)
            if m is None:
                continue
            elbname = m.group(1)
            logger.debug('IP %s is ENI (%s) for ELB "%s"', ip, desc, elbname)
            elbnames.add(elbname)
        for elbname in elbnames:
            elb_enis = list(self.ec2_res.network_interfaces.filter(Filters=[
                {'Name': 'description', 'Values': ['ELB %s' % elbname]},
                {'Name': 'subnet-id', 'Values': [subnet_id]}
            ]))
            logger.debug(
                'ELB "%s" appears to have %d ENIs currently',
                elbname, len(elb_enis)
            )
            curr_ips += len(elb_enis)
            max_ips += ELB_MAX_IPS
        return len(elbnames), curr_ips, max_ips

    def _handle_asgs(self, ips, subnet_id, ec2_ip_to_id):
        """
        Figure out the current number, and maximum number, of IPs for
        ASG instances in the subnet.

        :returns: Count of ASGs with instances in subnet, count of ASG instances
          currently in subnet, maximum number of ASG instances in subnet
        :rtype: tuple
        """
        curr_ips = 0
        max_ips = 0
        count = 0
        paginator = self.autoscaling.get_paginator(
            'describe_auto_scaling_groups'
        )
        for page in paginator.paginate():
            for asg in page['AutoScalingGroups']:
                subnets = asg['VPCZoneIdentifier'].split(',')
                if subnet_id not in subnets:
                    continue
                for inst in asg['Instances']:
                    if inst['InstanceId'] in ec2_ip_to_id.values():
                        curr_ips += 1
                max_ips += asg['MaxSize'] - len(asg['Instances'])
                count += 1
        return count, curr_ips, max_ips

    def _find_used_eni(self, subnet_id, _, ips):
        """find IPs in use by ENIs"""
        res = {}
        logger.debug('Querying ENIs within the subnet')
        for eni in self.ec2_res.network_interfaces.filter(
            Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}]
        ):
            for ipaddr in eni.private_ip_addresses:
                res[ipaddr['PrivateIpAddress']] = '%s / %s' % (
                    eni.id, eni.description
                )
        return res

    def _find_used_ec2_instances(self, subnet_id, _, ips, show_tags=False):
        """find IPs in use by EC2 instances"""
        res = {}
        logger.debug("Querying EC2 Instances within the subnet")
        paginator = self.ec2.get_paginator('describe_instances')
        # by network-interface.subnet-id
        resp = paginator.paginate(
            Filters=[{
                'Name': 'network-interface.subnet-id',
                'Values': [subnet_id]
            }]
        )
        for r in resp:
            for reservation in r['Reservations']:
                for inst in reservation['Instances']:
                    if inst['PrivateIpAddress'] in ips:
                        res[inst['PrivateIpAddress']] = inst['InstanceId']
                    elif inst.get('PublicIpAddress', None) in ips:
                        res[inst['PublicIpAddress']] = inst['InstanceId']
                    else:
                        for ni in inst['NetworkInterfaces']:
                            if ni['PrivateIpAddress'] in ips:
                                res[inst['PrivateIpAddress']] = inst[
                                    'InstanceId'] + '/' + inst.get('NetworkInterfaceId', '0')
        # by subnet-id
        resp = paginator.paginate(
            Filters=[{
                'Name': 'subnet-id',
                'Values': [subnet_id]
            }]
        )
        for r in resp:
            for reservation in r['Reservations']:
                for inst in reservation['Instances']:
                    if inst['PrivateIpAddress'] in ips:
                        res[inst['PrivateIpAddress']] = inst['InstanceId']
                    elif inst.get('PublicIpAddress', None) in ips:
                        res[inst['PublicIpAddress']] = inst['InstanceId']
                    else:
                        for ni in inst['NetworkInterfaces']:
                            if ni['PrivateIpAddress'] in ips:
                                res[inst['PrivateIpAddress']] = inst[
                                    'InstanceId'] + '/' + inst.get('NetworkInterfaceId', '0')
        return res

    def _ips_for_subnet(self, cidr):
        """return a list of all IPs in the subnet"""
        net = IPNetwork(cidr)
        ips = [str(x) for x in list(net[4:-1])]
        return ips

    def _find_subnet(self, query):
        """find a subnet by query (subnet ID or CIDR block)"""
        if re.match(r'^subnet-[a-fA-F0-9]+$', query):
            subnet = self._find_subnet_by_id(query)
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}', query):
            subnet = self._find_subnet_by_block(query)
        else:
            raise SystemExit(
                "ERROR: %s does not look like a subnet ID or CIDR block" % query
            )
        return subnet

    def _find_subnet_by_id(self, subnet_id):
        """find a subnet by subnet ID"""
        kwargs = {
            'SubnetIds': [subnet_id]
        }
        return self._find_classic_subnet(kwargs)

    def _find_subnet_by_block(self, cidr):
        """find a subnet by CIDR block"""
        kwargs = {
            'Filters': [
                {
                    'Name': 'cidrBlock',
                    'Values': [cidr]
                }
            ]
        }
        return self._find_classic_subnet(kwargs)

    def _find_classic_subnet(self, kwargs):
        """call describe_subnets passing kwargs"""
        logger.info("Querying for subnet")
        logger.debug("calling ec2.describe_subnets with args: %s", kwargs)
        try:
            subnets = self.ec2.describe_subnets(**kwargs)['Subnets']
        except ClientError:
            logger.debug("No Classic subnet found matching query.")
            return None
        logger.debug("Result: %s", subnets)
        if len(subnets) < 1:
            raise SystemExit("Error: 0 subnets found matching: %s" % kwargs)
        if len(subnets) > 1:
            raise SystemExit("Error: %s subnets found matching: %s" % (
                len(subnets), kwargs
            ))
        return subnets[0]


def parse_args(argv):
    """parse arguments/options"""
    p = argparse.ArgumentParser(description='Find AWS IP usage by subnet')
    p.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                   default=False, help='verbose output.')
    p.add_argument('-t', '--show-tags', dest='show_tags', action='store_true',
                   default=False, 
                   help='Show tags for NLBs and EKS instances.')
    p.add_argument('SUBNET_ID_OR_BLOCK', help='subnet_id or CIDR netmask')
    args = p.parse_args(argv)
    return args

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    finder = AWSIPUsage()
    finder.show_subnet_usage(args.SUBNET_ID_OR_BLOCK, args.show_tags)
