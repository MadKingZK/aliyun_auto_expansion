#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Introduce :
@File      : main.py
@Time      : 2021/4/10 23:29
@Author    : MadKingZK
@Emile     : harvey_dent@163.com
@pip       : pip install 
"""
from loguru import logger

import settings
import tools
from auto_expansion import EcsExpansionser


def main():
    # 初始化日志模块
    tools.logger_init()
    args = EcsExpansionser.args_parser()

    # 实例化ecs扩容器
    ecs_expansionser = EcsExpansionser(settings.key, settings.secret, settings.region, args.projname, args.amount)

    # 创建ecs实例
    instance_ids, error = ecs_expansionser.create_instances()
    if error:
        logger.error(f"创建实例失败，instance_ids: {instance_ids}, error: {error}")
        exit(1)

    # 获取主机信息
    ecs_expansionser.get_hosts_info()

    # 加入次要安全组（创建ecs时只能加入一个安全组）
    ecs_expansionser.join_secondary_security_group()

    # 设置classlink，经典网络机器连通vpc网络
    ecs_expansionser.set_classlink()

    # 调用初始化脚本，初始化ecs上的服务，启动服务
    ecs_expansionser.exec_init_shell_scripts()

    # 服务启动后，检查接口是否健康，返回服务健康的ecs实例id列表
    check_instances_ok = ecs_expansionser.check_api()

    # 将服务健康的ecs实例加入到指定slb中
    ecs_expansionser.add_instance_into_slb(check_instances_ok)

    # 将创建出的ecs加入到jms中
    ecs_expansionser.add_instance_into_jms()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(err)
