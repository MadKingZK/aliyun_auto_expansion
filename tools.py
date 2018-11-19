# -*- coding: utf-8 -*-
import json, time
import paramiko
import settings
import requests
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import DescribeDisksRequest, DescribeSnapshotsRequest, DescribeImagesRequest, \
    CreateImageRequest, DescribeInstancesRequest
from aliyunsdkslb.request.v20140515 import AddVServerGroupBackendServersRequest
from pyzabbix import ZabbixAPI


class AliEcsTools(object):
    def __init__(self, ali_key, ali_secret, region_id):
        self.ali_key = ali_key
        self.ali_secret = ali_secret
        self.client = AcsClient(
            self.ali_key,
            self.ali_secret,
        )
        self.region_id = region_id
        self.client.set_region_id(self.region_id)

    def get_disks(self, instance_id):
        request = DescribeDisksRequest.DescribeDisksRequest()
        request.set_InstanceId(instance_id)
        request.set_DiskType('all')
        request.set_Status('In_use')
        request.set_PageSize(20)
        response = self.client.do_action_with_exception(request)
        response_dic = json.loads(response)
        disks_info = response_dic.get('Disks').get('Disk')
        disk_lst = []
        for disk in disks_info:
            disk_lst.append({'DiskId': disk.get('DiskId'), 'Type': disk.get('Type'), 'Size': disk.get('Size')})
        return disk_lst

    def find_last_snapshot(self, disk_id):
        request = DescribeSnapshotsRequest.DescribeSnapshotsRequest()
        request.set_DiskId(disk_id)
        request.set_Status("accomplished")
        request.set_PageSize(10)
        pageNumber = 1
        request.set_PageNumber(pageNumber)

        response = self.client.do_action_with_exception(request)
        response_dict = json.loads(response)
        # 生成生成器
        while response_dict.get('Snapshots').get('Snapshot'):
            yield response_dict.get('Snapshots').get('Snapshot')
            pageNumber += 1
            request.set_PageNumber(pageNumber)
            response = self.client.do_action_with_exception(request)
            response_dict = json.loads(response)

    def get_last_snap_id(self, disk_id):
        ts_cur = 0
        last_snap_id = None
        for snaps in self.find_last_snapshot(disk_id):
            for snap in snaps:
                snap_id = snap.get('SnapshotId')
                ts = int(time.mktime(time.strptime(snap.get('CreationTime'), '%Y-%m-%dT%H:%M:%SZ')))
                last_snap_id, ts_cur = (snap_id, ts) if ts > ts_cur else (last_snap_id, ts_cur)
        return last_snap_id

    def get_image(self, snap_id):
        # 拿到快照id，检查快照id状态
        request = DescribeImagesRequest.DescribeImagesRequest()
        request.set_Status('Available')
        request.set_ImageOwnerAlias('self')
        request.set_PageNumber(1)
        request.set_PageSize(10)
        # 检查快照是否已经生成镜像，如果已经生成，则返回已生成的
        request.set_SnapshotId(snap_id)
        response = self.client.do_action_with_exception(request)
        response_dict = json.loads(response)
        images = response_dict.get('Images').get('Image')
        # 判断是否返回中有image，如果有则返回，如果没有则创建。
        if images:
            return images[0].get('ImageId')
        # 没有，创建新的镜像，检查镜像状态，创建成功后，返回镜像id。
        else:
            response = self.create_image(snap_id)
            return response

    def create_image(self, snap_id):
        # 拿到快照id，检查快照id状态
        request = CreateImageRequest.CreateImageRequest()
        request.set_SnapshotId(snap_id)
        request.set_ImageName(
            "auto_expansion_{date_time}".format(date_time=time.strftime('%Y-%m-%d_%H:%M', time.localtime(time.time()))))
        response = self.client.do_action_with_exception(request)
        print(response)

    def add_to_slb(self, svid, instance_ids, weight):
        request = AddVServerGroupBackendServersRequest.AddVServerGroupBackendServersRequest()
        request.set_VServerGroupId(svid)
        backend_servers = [{"ServerId": instance_id, "Port": "80", "Weight": weight, "Type": "ecs"} for instance_id in
                           instance_ids]
        request.set_BackendServers(backend_servers)
        response = self.client.do_action_with_exception(request)
        print(response)

    def get_instance_info(self, instancd_ids):
        pageNumber = 1
        request = DescribeInstancesRequest.DescribeInstancesRequest()
        request.set_InstanceIds(instancd_ids)
        request.set_accept_format('json')
        request.set_PageSize(10)
        request.set_PageNumber(pageNumber)

        # 发起API请求并显示返回值
        response = self.client.do_action_with_exception(request)
        response_dict = json.loads(response)
        print(response_dict)

        # 生成生成器
        while response_dict['Instances']['Instance']:
            yield response_dict['Instances']['Instance']
            pageNumber += 1
            request.set_PageNumber(pageNumber)
            response = self.client.do_action_with_exception(request)
            response_dict = json.loads(response)


class SshTools(object):
    def __init__(self, host):
        __private_key = paramiko.RSAKey.from_private_key_file(settings.ssh_keyfile)

        # 创建SSH对象
        self.ssh = paramiko.SSHClient()
        # 允许连接不在know_hosts文件中的主机
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 连接服务器
        self.ssh.connect(hostname=host, port=22, username='root', pkey=__private_key)

    def execute_cmd(self, cmd):
        # 执行命令
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        # 获取命令结果
        channel = stdout.channel
        status = channel.recv_exit_status()
        out = stdout.readlines()
        err = stderr.readlines()
        return status, out, err


class ZbxApiTools(object):
    def __init__(self, user, password, url):
        self.prioritytostr = {'0': 'ok', '1': '信息', '2': '警告', '3': '严重'}  # 告警级别
        self.user = user
        self.password = password
        self.url = url
        self.zapi = ZabbixAPI(self.url)
        self.zapi.login(self.user, self.password)

    def getHosts(self):
        hosts = self.zapi.host.get(
            output="extend",
            hostids="10321",
            monitored_hosts=None,
        )
        return hosts

def check_api(host,group_name):
    check_dic = settings.check_api.get(group_name)
    uri = check_dic.get('uri')
    headers = check_dic.get('headers')
    data = check_dic.get('data')
    res = requests.post(check_dic.get('proto')+host+uri, data=data, headers=headers)
    if res.status_code == requests.codes.ok:
        return True
    else:
        return False


if __name__ == '__main__':
    pass
