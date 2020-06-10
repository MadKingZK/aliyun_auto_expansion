# encoding:utf-8
import os
import time
import sys
import argparse
import settings
import tools
from collect_param import collect_param
from create_ecs import AliCreateInstances


def main():
    parser = argparse.ArgumentParser(description="auto expansion args")
    parser.add_argument("-p", "--prjName", type=str, required=True, help="需要扩容的项目名称")
    parser.add_argument(
        "-n",
        "--amount",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        required=True,
        help="需要扩容的节点数",
    )
    args = parser.parse_args()
    prjname = args.prjName
    amount = args.amount
    exit(1)
    if prjname not in settings.ecs_info.keys():
        print("wrong arg, needs {keys} ".format(keys=settings.ecs_info.keys()))
        sys.exit(2)
    elif not amount.isdigit():
        print("amount of ecs arg needs digit (1-9)")
        sys.exit(3)
    elif int(amount) >= 10:
        print("amount of ecs arg must in [1-9]")
        sys.exit(4)
    ecs_info = collect_param(prjname)
    amount = int(amount)

    # print(ecs_info)
    instance_types = ecs_info.get("instance_types")
    instance_ids = None
    for instance_type in instance_types:
        ecs_info["instance_type"] = instance_type
        instance_ids = AliCreateInstances(ecs_info, amount).run()
        if isinstance(instance_ids, int):
            print(instance_type)
            if instance_ids == 404:
                print("实例已售空，创建下一个实例类型")
                continue
            elif instance_ids == 201:
                print("Dry Run 参数检查通过")
                sys.exit(0)
        elif isinstance(instance_ids, list):
            break
        else:
            print(
                "创建实例返回的instance_id格式错误：{instance_ids}".format(
                    instance_ids=instance_ids
                )
            )
            sys.exit(1)
    if not isinstance(instance_ids, list):
        sys.exit(1)

    # 获取创建出来的instance的ip
    newecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
    newecs_infos = []
    for infos in newecs.get_instance_info(instance_ids):
        newecs_infos.extend(infos)

    hostinfos = {
        info.get("InnerIpAddress").get("IpAddress")[0]: info.get("InstanceName")
        for info in newecs_infos
    }
    print(instance_ids)
    print(hostinfos)
    time.sleep(20)

    # 添加次要安全组
    for instance_id in instance_ids:
        for security_group_id in ecs_info.get("secondry_secrity_group_ids"):
            res = newecs.join_security_group(instance_id, security_group_id)
            print("成功执行，返回值为：{res}".format(res=res))
            print(
                "instance:{instance_id} 已添加次要安全组:{security_group_id} 中".format(
                    instance_id=instance_id, security_group_id=security_group_id
                )
            )
    # 执行初始化脚本。
    for ip, hostname in hostinfos.items():
        print(hostinfos)
        try:
            init_script = ecs_info.get("init_script")
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
                print(" remote command error info : %s" % error_info)
                print(error_info)
                return None
            if status == 0:
                print("主机{hostname} {ip}初始化成功".format(hostname=hostname, ip=ip))
                print("输出信息: {out}".format(out=stdout))
        except Exception as err:
            print(err)
            print("主机服务初始化失败！！！")
    time.sleep(10)
    # 检查带访问mongo和redis的api，是否可正常返回数据
    check_instances_ok = []
    for ip in hostinfos.keys():
        try:
            if tools.check_api(ip, prjname):
                for info in newecs_infos:
                    if ip == info.get("InnerIpAddress").get("IpAddress")[0]:
                        check_instances_ok.append(info.get("InstanceId"))
        except Exception as err:
            print(err)
            print("检查接口时出错！！！")
    print(check_instances_ok)

    # 添加到slb中，阈值在settings中取到
    try:
        weight = ecs_info.get("slb_weight")
        for svid in ecs_info.get("slb_vids"):
            ecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
            ecs.add_to_slb(svid, check_instances_ok, weight)
    except Exception as err:
        print("instance 添加到SLB失败！！！")

    print("扩容已完成，开始加入jumpserver中。")
    # 添加到jumpserver和zabbix中
    jmp_client = tools.JumpServerClient(
        settings.jms_url, settings.jms_username, settings.jms_password
    )
    jmp_client.login()
    zbx_client = tools.ZabbixMonitor(
        settings.zbx_url, settings.zbx_username, settings.zbx_password
    )
    zbx_groupids = ecs_info.get("zbx_groupids")
    zbx_templateids = ecs_info.get("zbx_templateids")
    for ip, hostname in hostinfos.items():
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
            print("{hostname}: {ip}已成功加入jumpserver！！！".format(hostname=hostname, ip=ip))
        except Exception as err:
            print(err)
            print("{hostname}: {ip}加入jumpserver时出错！！！".format(hostname=hostname, ip=ip))
        if zbx_groupids and zbx_templateids:
            try:
                zbx_client.add_into_zabbix(hostname, ip, zbx_groupids, zbx_templateids)
                print("{hostname}: {ip}已成功加入zabbix！！！".format(hostname=hostname, ip=ip))
            except Exception as err:
                print(err)
                print("{hostname}: {ip}已成功加入zabbix！！！".format(hostname=hostname, ip=ip))
        else:
            print("未加入到zabbix中，未获取到该主机组关于zabbix的配置，请查看配置文件。")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(err)
