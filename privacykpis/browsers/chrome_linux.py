import os
from pathlib import Path
import shutil
import subprocess
import time
import getpass

from privacykpis.args import MeasureArgs, ConfigArgs
from privacykpis.consts import LEAF_CERT


POLICIES_DIR_PATH = Path("/etc/opt/chrome/policies/recommended")
POLICIES_FILE_PATH = POLICIES_DIR_PATH / Path("recommended_policies.json")

USER_CERT_DB_PATH = Path.home() / Path(".pki/nssdb")
USER_CERT_DB = "sql:{}".format(str(USER_CERT_DB_PATH))


def launch_browser(args: MeasureArgs):
    # Sneak this in here because there are problems running Xvfb
    # as sudo, and sudo is needed for the *_env functions.
    from xvfbwrapper import Xvfb

    args = [
        args.binary,
        "--user-data-dir=" + args.profile_path,
        "--proxy-server={}:{}".format(args.proxy_host, args.proxy_port),
        args.url
    ]
    xvfb_handle = Xvfb()
    xvfb_handle.start()
    return [subprocess.Popen(args), xvfb_handle]


def close_browser(args: MeasureArgs, browser_info):
    browser_handle, xvfb_handle = browser_info
    browser_handle.terminate()
    xvfb_handle.stop()


def setup_env(args: ConfigArgs):
    target_user = getpass.getuser()
    setup_args = [
        # Create the nssdb directory for this user.
        ["mkdir", "-p", str(USER_CERT_DB_PATH)],
        # Create an empty CA container / database.
        ["certutil", "-N", "-d", USER_CERT_DB, "--empty-password"],
        # Add the mitmproxy cert to the newly created database.
        ["certutil", "-A", "-d", USER_CERT_DB, "-i", str(LEAF_CERT), "-n",
            "mitmproxy", "-t", "TC,TC,TC"]
    ]
    sudo_prefix = ["sudo", "-u", target_user]
    for args in setup_args:
        subprocess.run(sudo_prefix + args)


def teardown_env(args: ConfigArgs):
    target_user = getpass.getuser()
    subprocess.run([
        "sudo", "-u", target_user, "certutil", "-D", "-d", USER_CERT_DB, "-n",
        "mitmproxy"])
