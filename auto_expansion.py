import tools, settings, os, time, sys
from collect_param import collect_param
from create_ecs import AliCreateInstances


def main():
    if len(sys.argv) <= 2:
        arg1 = None
        arg2 = None
        print('need appGroup arg just like "php-main" and amount of ecs arg')
        exit(1)
    else:
        arg1 = sys.argv[1]
        arg2 = sys.argv[2]
    if arg1 not in settings.ecs_info.keys():
        print('wrong arg, needs {keys} '.format(keys=settings.ecs_info.keys()))
        exit(2)
    elif not arg2.isdigit():
        print('amount of ecs arg needs digit (1-9)')
        exit(3)
    elif int(arg2) >= 10:
        print('amount of ecs arg must in [1-9]')
        exit(4)
    ecs_info = collect_param(arg1)
    arg2 = int(arg2)
    #print(ecs_info)
    instance_ids = AliCreateInstances(ecs_info, arg2).run()
    #获取创建出来的instance的ip
    newecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
    newecs_infos = [info for info in newecs.get_instance_info(instance_ids)]

    ips = [info[0].get('InnerIpAddress').get('IpAddress')[0] for info in newecs_infos]
    print(instance_ids)
    print(ips)
    time.sleep(10)
    # 执行初始化脚本。
    for ip in ips:
        try:
            init_script = ecs_info.get('init_script')
            home_path = os.path.split(os.path.realpath(__file__))[0]
            os.system(
                'scp -o "StrictHostKeyChecking no" {home_path}/{init_script} root@{ip}:/root/auto_init.sh '.format(home_path=home_path,
                                                                                               init_script=init_script,
                                                                                               ip=ip))
            ssh = tools.SshTools(ip)
            cmd = settings.init_cmd
            status, out, err = ssh.execute_cmd(cmd)
            if status == 0:
                print('主机{ip}初始化成功'.format(ip=ip))
                print('输出信息: {out}'.format(out=out))
        except Exception as err:
            print(err)
            print('主机服务初始化失败！！！')
    time.sleep(10)
    # 检查带访问mongo和redis的api，是否可正常返回数据
    check_instances_ok = []
    for ip in ips:
        try:
            if tools.check_api(ip, arg1):
                for info in newecs_infos:
                    if ip == info[0].get('InnerIpAddress').get('IpAddress')[0]:
                        check_instances_ok.append(info[0].get('InstanceId'))
        except Exception as err:
            print(err)
            print('检查接口时出错！！！')
    print(check_instances_ok)

    #添加到slb中，阈值在settings中取到
    try:
        weight = ecs_info.get('slb_weight')
        for svid in ecs_info.get('slb_vids'):
            ecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
            ecs.add_to_slb(svid, check_instances_ok, weight)
    except Exception as err:
        print('instance 添加到SLB失败！！！')
    # 添加到zabbix中

    # 添加到jumpserver中


if __name__ == '__main__':
    main()
