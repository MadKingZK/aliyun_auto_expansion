# 阿里云API验证key与秘钥
key = "mykey"
secret = "mysecret"
region = "cn-beijing"
ssh_keyfile = "/root/.ssh/id_rsa"
init_cmd = "bash /root/auto_init.sh"

jms_url = "https://jumpserver.example.cn/"
jms_username = "jmsusername"
jms_password = "jmspwd"

zbx_url = "http://zabbix.example.cn"
zbx_username = "zbxusername"
zbx_password = "zbxpwd"

check_api = {
    "php-main": {
        # 检查的接口最好是可以同时查询redis和db的，可以更好的检查部署的项目是否健康。
        "proto": "http://",
        "uri": "/aaa/bbb",
        "headers": {"Content-Type": "application/json", "charset": "utf-8",},
        "data": {"token": "", "qs": ""},
    },
}


# 是否只预检此次请求。true：发送检查请求，不会创建实例，也不会产生费用；false：发送正常请求，通过检查后直接创建实例，并直接产生费用
dry_run = False

ecs_info = {
    "xng-php-main": {
        # 设置参照ECS模板
        "ecs_model_id": "",
        # 设置默认安全组，在创建ECS时指定添加
        "default_secrity_group_id": "",
        # 设置次要安全组，在创建ECS完成后指定添加
        "secondry_secrity_group_ids": [""],
        # 实例类型（cpu与内存）按优先级排序，在前一个创建失败或者指定返回为缺货后尝试下一个，都尝试完如果失败则报错。
        "instance_types": ["ecs.sn1.3xlarge"],
        #'instance_types': ['ecs.sn1.3xlarge','ecs.n4.4xlarge', 'ecs.n1.3xlarge'],
        #'instance_types': ['ecs.n1.tiny'],
        # 设置实例创建所在可用区
        "zone_id": "cn-beijing-b",
        # 网卡付费类型，按量或者包年包月
        "internet_charge_type": "PayByTraffic",
        # 带宽最大值
        "internet_max_bandwidth_out": 1,
        # 设置初始化脚本
        "init_script": "php_init.sh",
        # 需要添加到的slb服务器组id
        "slb_vids": [
            "rsp-wz961asdfasdf",
            "rsp-wz9asdfasdf",
            "rsp-wz91asdfasdf",
            "rsp-wz9asdfasdf",
        ],
        "slb_weight": 0,
        "zbx_groupids": [{"groupid": 19}, {"groupid": 57}],
        "zbx_templateids": [10095, 10453],
    },
    "xng-go": {},
    "xng-op": {},
    "xbd-php": {},
    "xbd-go": {},
    "xbd-op": {},
    "wk-php": {},
    "wk-go": {},
    "wk-op": {},
}
