import settings
import tools
import time

def collect_param(ecs_group):
    ecs_info = settings.ecs_info[ecs_group]
    ecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
    date_time = time.strftime('%Y-%m-%d_%H-%M', time.localtime(time.time()))
    ecs_info['instance_name'] = '{ecs_group}_{date_time}-'.format(ecs_group=ecs_group, date_time=date_time)
    disk_lst = ecs.get_disks(ecs_info.get('ecs_model_id'))
    for i in range(len(disk_lst)):
        last_snap_id = ecs.get_last_snap_id(disk_lst[i].get('DiskId'))
        disk_lst[i]['LastSnapId'] = last_snap_id

    for disk in disk_lst:
        if disk.get('Type') == 'system':
            snap_id = disk.get('LastSnapId')
            image_id = ecs.get_image(snap_id)
            ecs_info['ImageId'] = image_id
            ecs_info['Disks'] = disk_lst
            break

    return ecs_info

if __name__ == '__main__':
    pass
