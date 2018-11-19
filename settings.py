# 阿里云API验证key与秘钥
key = ''
secret = ''
region = 'cn-shenzhen'
ssh_keyfile = '/root/.ssh/id_rsa'
init_cmd = 'bash /root/auto_init.sh'

check_api = {
    'xng-php-main': {
        'proto': 'http://',
        'uri': '/tarns/check_api.php',
        'headers': {
            'Content-Type': 'application/json',
            'charset': 'utf-8',
        },
        'data': {
            "token": "aaaa",
            "check": True,
        }
    },
}


# 是否只预检此次请求。true：发送检查请求，不会创建实例，也不会产生费用；false：发送正常请求，通过检查后直接创建实例，并直接产生费用
dry_run = True

ecs_info = {
    'xng-php-main': {
        # 设置参照ECS模板
        'ecs_model_id': 'o-afefajorrcwsawef',
        # 设置默认安全组，在创建ECS时指定添加
        'default_secrity_group_id': 'ef-fwfefo45g',
        # 设置次要安全组，在创建ECS完成后指定添加
        'secondry_secrity_group_ids': ['ger-wefwewef1'],
        # 实例类型（cpu与内存）按优先级排序，在前一个创建失败或者指定返回为缺货后尝试下一个，都尝试完如果失败则报错。
        # 'instance_types': ['ecs.sn1.3xlarge'],
        'instance_types': ['ecs.n1.tiny'],
        # 设置实例创建所在可用区
        'zone_id': 'cn-shenzhen-a',
        # 设置初始化脚本
        'init_script': 'php_init.sh',
        #需要添加到的slb服务器组id
        'slb_vids': ['wefwfwef', 'wefwefwef'],
        'slb_weight': 45,
    },
    'xng-go': {

    },
    'xng-op': {

    },
    'xbd-php': {

    },
    'xbd-go': {

    },
    'xbd-op': {

    },
    'wk-php': {

    },
    'wk-go': {

    },
    'wk-op': {

    },
}
