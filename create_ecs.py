# coding=utf-8
import json
import time
import traceback
import settings
import copy

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkecs.request.v20140526.RunInstancesRequest import RunInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import (
    DescribeInstancesRequest,
)

RUNNING_STATUS = "Running"
CHECK_INTERVAL = 3
CHECK_TIMEOUT = 180


class AliCreateInstances(object):
    def __init__(self, ecs_info, amount=1):
        self.ecs_info = ecs_info
        self.access_id = settings.key
        self.access_secret = settings.secret

        # 是否只预检此次请求。true：发送检查请求，不会创建实例，也不会产生费用；false：发送正常请求，通过检查后直接创建实例，并直接产生费用
        self.dry_run = settings.dry_run
        # 实例所属的地域ID
        self.region_id = settings.region
        # 实例的计费方式
        self.instance_charge_type = "PostPaid"
        # 购买资源的时长
        self.period = 1
        # 购买资源的时长单位
        self.period_unit = "Hourly"
        # 实例所属的可用区编号
        self.zone_id = self.ecs_info.get("zone_id")
        # 网络计费类型
        self.internet_charge_type = self.ecs_info.get("internet_charge_type")
        # 镜像ID
        self.image_id = self.ecs_info.get("ImageId")
        # 指定新创建实例所属于的安全组ID
        self.security_group_id = self.ecs_info.get("default_secrity_group_id")
        # 实例名称
        self.instance_name = self.ecs_info.get("instance_name")
        # 是否使用镜像预设的密码
        self.password_inherit = True
        # 指定创建ECS实例的数量
        self.amount = amount
        # 公网出带宽最大值
        self.internet_max_bandwidth_out = self.ecs_info.get(
            "internet_max_bandwidth_out"
        )
        # 是否为实例名称和主机名添加有序后缀
        self.unique_suffix = True
        # 是否为I/O优化实例
        self.io_optimized = "optimized"
        # 是否开启安全加固
        self.security_enhancement_strategy = "Active"
        # 实例的资源规格
        self.instance_type = self.ecs_info.get("instance_type")
        # 系统盘大小
        self.system_disk_size = "40"
        # 系统盘的磁盘种类
        self.system_disk_category = "cloud_efficiency"
        # 数据盘
        self.data_disks = [
            {
                "Size": disk.get("Size"),
                "SnapshotId": disk.get("LastSnapId"),
                "Category": "cloud_efficiency",
                "DeleteWithInstance": True,
            }
            for disk in ecs_info.get("Disks")
            if disk.get("Type") == "data"
        ]
        # print(self.data_disks)
        self.client = AcsClient(self.access_id, self.access_secret, self.region_id)

    def run(self):
        try:
            ids = self.run_instances()
            check_ids = copy.deepcopy(ids)
            self._check_instances_status(check_ids)
            return ids, 200, None
        except ClientException as e:
            error = "Fail. Something with your connection with Aliyun go incorrect. Code: {code}, Message: {msg}".format(code=e.error_code, msg=e.message)
            return [], 500, error
        except ServerException as e:
            error = "Fail. Business error. Code: {code}, Message: {msg}".format(code=e.error_code, msg=e.message)
            if e.error_code == "OperationDenied.NoStock":
                return [], 404, error
            elif e.error_code == "DryRunOperation":
                return [], 201, error
        except Exception:
            print("Unhandled error")
            print(traceback.format_exc())
            return [], 500, "Unhandled error"

    def run_instances(self):
        """
        调用创建实例的API，得到实例ID后继续查询实例状态
        :return:instance_ids 需要检查的实例ID
        """
        request = RunInstancesRequest()

        request.set_DryRun(self.dry_run)

        request.set_InstanceChargeType(self.instance_charge_type)
        request.set_Period(self.period)
        request.set_PeriodUnit(self.period_unit)
        request.set_ZoneId(self.zone_id)
        request.set_InternetChargeType(self.internet_charge_type)
        request.set_ImageId(self.image_id)
        request.set_SecurityGroupId(self.security_group_id)
        request.set_InstanceName(self.instance_name)
        request.set_PasswordInherit(self.password_inherit)
        request.set_Amount(self.amount)
        request.set_InternetMaxBandwidthOut(self.internet_max_bandwidth_out)
        request.set_UniqueSuffix(self.unique_suffix)
        request.set_IoOptimized(self.io_optimized)
        request.set_SecurityEnhancementStrategy(self.security_enhancement_strategy)
        request.set_InstanceType(self.instance_type)
        request.set_SystemDiskSize(self.system_disk_size)
        request.set_SystemDiskCategory(self.system_disk_category)
        request.set_DataDisks(self.data_disks)

        body = self.client.do_action_with_exception(request)
        data = json.loads(body)
        instance_ids = data["InstanceIdSets"]["InstanceIdSet"]
        print(
            "Success. Instance creation succeed. InstanceIds: {}".format(
                ", ".join(instance_ids)
            )
        )
        return instance_ids

    def _check_instances_status(self, instance_ids):
        """
        每3秒中检查一次实例的状态，超时时间设为3分钟.
        :param instance_ids 需要检查的实例ID
        :return:
        """
        start = time.time()
        while True:
            request = DescribeInstancesRequest()
            request.set_InstanceIds(json.dumps(instance_ids))
            body = self.client.do_action_with_exception(request)
            data = json.loads(body)
            for instance in data["Instances"]["Instance"]:
                if RUNNING_STATUS in instance["Status"]:
                    instance_ids.remove(instance["InstanceId"])
                    print(
                        "Instance boot successfully: {}".format(instance["InstanceId"])
                    )

            if not instance_ids:
                print("Instances all boot successfully")
                break

            if time.time() - start > CHECK_TIMEOUT:
                print(
                    "Instances boot failed within {timeout}s: {ids}".format(
                        timeout=CHECK_TIMEOUT, ids=", ".join(instance_ids)
                    )
                )
                break

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    pass
