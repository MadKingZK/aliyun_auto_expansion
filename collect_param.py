import time
import operator
import settings
import tools


def collect_param(ecs_group):
    ecs_info = settings.ecs_info[ecs_group]
    ecs = tools.AliEcsTools(settings.key, settings.secret, settings.region)
    timestep = time.strftime("%H%M%S", time.localtime(time.time()))
    ecs_info["instance_name"] = "{ecs_group}-{timestep}-".format(
        ecs_group=ecs_group, timestep=timestep
    )
    disk_lst = ecs.get_disks(ecs_info.get("ecs_model_id"))
    sorted_disk_lst = sorted(disk_lst, key=operator.itemgetter("Device"))
    for i in range(len(sorted_disk_lst)):
        last_snap_id = ecs.get_last_snap_id(sorted_disk_lst[i].get("DiskId"))
        sorted_disk_lst[i]["LastSnapId"] = last_snap_id

    for disk in sorted_disk_lst:
        if disk.get("Type") == "system":
            snap_id = disk.get("LastSnapId")
            image_id = ecs.get_image(snap_id)
            ecs_info["ImageId"] = image_id
            ecs_info["Disks"] = sorted_disk_lst
            break

    return ecs_info


if __name__ == "__main__":
    ecs_info = collect_param("php-main")
    print(ecs_info)
