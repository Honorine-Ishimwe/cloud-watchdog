from tools.list_resources import list_resources
from tools.get_disks import get_disks
from tools.get_public_ips import get_public_ips


def test_list_resources_returns_two_cards():
    result = list_resources("rg-watchdog-test")
    assert len(result) == 2


def test_disk_is_unattached():
    disk = get_disks("rg-watchdog-test")[0]
    assert disk["diskState"] == "Unattached"


def test_public_ip_is_not_attached():
    ip = get_public_ips("rg-watchdog-test")[0]
    assert ip["ipConfiguration"] is None
