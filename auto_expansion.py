# encoding:utf-8
import os
import time
from loguru import logger
import argparse
import settings
import tools
from collect_param import collect_param
from create_ecs import AliCreateInstances


class EcsExpansionser(tools.AliEcsTools):

    def __init__(self, ali_key, ali_secret, region_id, project_name, amount):
        super().__init__(ali_key, ali_secret, region_id)
        self.new_ecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
        self.project_name = project_name
        self.amount = amount
        self.ecs_info = collect_param(project_name)
        # 创建出来的阿里云实例列表，通过crate_instances获得
        self.instance_ids = []
        self.hosts_info = {}
        self.new_ecs_infos = []

    # create_instances 创建阿里云ecs实例
    def create_instances(self):
        instance_ids = []
        error = None
        for instance_type in self.ecs_info.get("instance_types"):
            self.ecs_info["instance_type"] = instance_type
            instance_ids, status, error = AliCreateInstances(self.ecs_info, self.amount).run()
            if error:
                if status == 404:
                    error = "实例已售空，创建下一个实例类型" + error
                    continue
                elif status == 201:
                    error = "Dry Run 参数检查通过" + error
                logger.error(error)
            elif instance_ids:
                break
            else:
                error = "创建实例返回的instance_id格式错误：{instance_ids}".format(instance_ids=instance_ids)
                logger.error(error)
            self.instance_ids = instance_ids
        return instance_ids, error

    # get_hosts_info 获取主机信息
    def get_hosts_info(self):
        for infos in self.new_ecs.get_instance_info(self.instance_ids):
            self.new_ecs_infos.extend(infos)

        hosts_info = {
            info.get("InnerIpAddress").get("IpAddress")[0]: info.get("InstanceName")
            for info in self.new_ecs_infos
        }
        self.hosts_info = hosts_info
        return hosts_info

    # join_secondary_security_group 加入次要安全组
    def join_secondary_security_group(self):
        # 添加次要安全组
        for instance_id in self.instance_ids:
            for security_group_id in self.ecs_info.get("secondry_secrity_group_ids"):
                res = self.new_ecs.join_security_group(instance_id, security_group_id)
                print("成功执行，返回值为：{res}".format(res=res))
                print(
                    "instance:{instance_id} 已添加次要安全组:{security_group_id} 中".format(
                        instance_id=instance_id, security_group_id=security_group_id
                    )
                )

    # set_classlink 设置classlink
    def set_classlink(self):
        for instance_id in self.instance_ids:
            # 如果settings中有key: vpc_id, 则添加可访问class_link（可访问vpc权限）
            if self.ecs_info.get("vpc_id"):
                res = self.new_ecs.cfg_attach_vpc(
                    instance_id, settings.region, self.ecs_info.get("vpc_id")
                )
                print("成功执行，返回值为：{res}".format(res=res))
                print(
                    "instance:{instance_id} 已添ClassLink:{vpc_id} 中".format(
                        instance_id=instance_id, vpc_id=self.ecs_info.get("vpc_id")
                    )
                )

    # exec_init_shell_scripts 执行初始化脚本
    def exec_init_shell_scripts(self):
        # 执行初始化脚本。
        for ip, hostname in self.hosts_info.items():
            print(self.hosts_info)
            try:
                init_script = self.ecs_info.get("init_script")
                home_path = os.path.split(os.path.realpath(__file__))[0]
                os.system('ssh-keygen -f "/root/.ssh/known_hosts" -R {ip}'.format(ip=ip))
                os.system(
                    'scp -o "StrictHostKeyChecking no" {home_path}/{init_script} root@{ip}:/root/auto_init.sh'.format(
                        home_path=home_path, init_script=init_script, ip=ip
                    )
                )
                ssh = tools.SshTools(ip)
                cmd = settings.init_cmd + "  " + hostname
                status, stdout, stderr = ssh.execute_cmd(cmd)
                error_info = stderr.read()
                if error_info and error_info.strip():
                    error = f" remote command error info : {error_info}"
                    logger.error(error)
                    return None
                if status == 0:
                    logger.info(f"主机{hostname} {ip}初始化成功")
                    logger.info("输出信息: {out}".format(out=stdout))
            except Exception as error:
                logger.error(f"主机服务初始化失败！！！{error}")
        time.sleep(10)

    # check_api 检查带访问mongo和redis的api，是否可正常返回数据
    def check_api(self):
        check_instances_ok = []
        for ip in self.hosts_info.keys():
            try:
                if tools.check_api(ip, self.project_name):
                    for info in self.new_ecs_infos:
                        if ip == info.get("InnerIpAddress").get("IpAddress")[0]:
                            check_instances_ok.append(info.get("InstanceId"))
            except Exception as error:
                logger.error(f"检查接口时出错！！！{error}")
        return check_instances_ok

    # add_instance_into_slb 添加到slb中，阈值在settings中取到
    def add_instance_into_slb(self, instance_ids):
        try:
            weight = self.ecs_info.get("slb_weight")
            for svid in self.ecs_info.get("slb_vids"):
                ecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
                ecs.add_to_slb(svid, instance_ids, weight)
        except Exception as error:
            logger.error(f"instance 添加到SLB失败！！！{error}")

        logger.info("扩容已完成，开始加入jumpserver中。")

    # add_instance_into_jms 添加到jumpserver和zabbix中
    def add_instance_into_jms(self):
        jmp_client = tools.JumpServerClient(
            settings.jms_url, settings.jms_username, settings.jms_password
        )
        jmp_client.login()
        zbx_client = tools.ZabbixMonitor(
            settings.zbx_url, settings.zbx_username, settings.zbx_password
        )
        zbx_groupids = self.ecs_info.get("zbx_groupids")
        zbx_templateids = self.ecs_info.get("zbx_templateids")
        for ip, hostname in self.hosts_info.items():
            try:
                jmp_client.create_assets(
                    ip,
                    hostname,
                    "2d6371ba8130404981930831cbb1de1e",
                    [
                        "847af37266f54eb895654af2c047ea7e",
                        "cb83effd186b4d43bee794c8d5b1150b",
                    ],
                )
                logger.info(f"{hostname}: {ip}已成功加入jumpserver！！！")
            except Exception as error:
                logger.error(f"{hostname}: {ip}加入jumpserver时出错！！！{error}")
            if zbx_groupids and zbx_templateids:
                try:
                    zbx_client.add_into_zabbix(hostname, ip, zbx_groupids, zbx_templateids)
                    logger.info(f"{hostname}: {ip}已成功加入zabbix！！！")
                except Exception as error:
                    logger.error(f"{hostname}: {ip}已成功加入zabbix！！！{error}")
            else:
                logger.error("未加入到zabbix中，未获取到该主机组关于zabbix的配置，请查看配置文件。")

    # 解析脚本调用时传入的参数
    @ staticmethod
    def args_parser():
        # 解析参数
        parser = argparse.ArgumentParser(description="auto expansion args")
        parser.add_argument(
            "-p",
            "--prjName",
            type=str,
            choices=settings.ecs_info.keys(),
            required=True,
            help="需要扩容的项目名称",
        )
        parser.add_argument(
            "-n",
            "--amount",
            type=int,
            choices=[i for i in range(1, 10)],
            required=True,
            help="需要扩容的节点数",
        )

        args = parser.parse_args()
        return args

