import json
import os
import pathlib
import platform
import pwd
from subprocess import Popen, PIPE
from time import sleep

from privacykpis.args import MeasureArgs, ConfigArgs, Args
from privacykpis.consts import CERT_PATH, LOG_HEADERS_SCRIPT_PATH

import privacykpis.browsers.firefox_linux as firefox_linux_module
import privacykpis.browsers.firefox_macos as firefox_macos_module
import privacykpis.browsers.chrome_linux as chrome_linux_module
import privacykpis.browsers.safari as safari_module


def get_real_user():
    return pathlib.Path.home().owner()


def module_for_args(args: Args):
    platform_name = platform.system()
    is_linux = platform_name == "Linux"
    is_mac = platform_name == "Darwin"

    case_module = None
    if args.case == "safari":
        if is_mac:
            case_module = safari_module
    elif args.case == "chrome":
        if is_linux:
            case_module = chrome_linux_module
    elif args.case == "firefox":
        if is_mac:
            case_module = firefox_macos_module
        elif is_linux:
            case_module = firefox_linux_module

    if case_module is None:
        msg = "{} on {} is not currently implemented".format(
            args.case, platform_name)
        raise RuntimeError(msg)

    return case_module


def setup_proxy_for_url(args: MeasureArgs):
    mitmdump_args = [
        "mitmdump",
        "--listen-host", args.proxy_host,
        "--listen-port", args.proxy_port,
        "-s", str(LOG_HEADERS_SCRIPT_PATH),
        "--set", "confdir=" + str(CERT_PATH),
        "-q",
        json.dumps(dict(privacy_kpis_url=args.url, privacy_kpis_log=args.log))
    ]

    proxy_handle = Popen(mitmdump_args, stderr=None)
    if args.debug:
        print("Waiting 5 sec for mitmproxy to spin up...")
    sleep(5)
    if proxy_handle.poll() is not None:
        print("Something went sideways when running mitmproxy:")
        print("\t" + " ".join(mitmdump_args))
        return None

    return proxy_handle


def teardown_proxy(proxy_handle, args: MeasureArgs):
    if args.debug:
        print("Shutting down, giving proxy time to write log")
    proxy_handle.terminate()
    proxy_handle.wait()


def record(args: MeasureArgs):
    case_module = module_for_args(args)
    proxy_handle = setup_proxy_for_url(args)
    if proxy_handle is None:
        return

    browser_info = case_module.launch_browser(args)
    if args.debug:
        print("browser loaded, waiting {} secs".format(args.secs))
    sleep(args.secs)
    if args.debug:
        print("measurement complete, tearing down")
    case_module.close_browser(args, browser_info)

    teardown_proxy(proxy_handle, args)


def configure_env(args: ConfigArgs):
    case_module = module_for_args(args)
    if args.install:
        case_module.setup_env(args)
    else:  # uninstall path.
        case_module.teardown_env(args)
