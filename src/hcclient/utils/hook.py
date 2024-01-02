# Author:    AnnikaV9
# License:   Unlicense

import os
import sys
import importlib.util

import packaging.version
import packaging.specifiers

from hcclient import meta


def check_hook(module: object) -> bool:
    """
    Checks if a hook has the required attributes
    """
    if not hasattr(module, "HookInfo"):
        return False

    if not hasattr(module.HookInfo, "name") or not hasattr(module.HookInfo, "version"):
        return False

    if not isinstance(module.HookInfo.name, str) or not isinstance(module.HookInfo.version, str):
        return False

    if not module.HookInfo.name.isalnum():
        return False

    try:
        packaging.version.parse(module.HookInfo.version)

    except packaging.version.InvalidVersion:
        return False

    return True


def check_compat(hook_info: object) -> bool:
    """
    Checks if a hook's version is compatible with the client's version
    """
    client_version = packaging.version.parse(meta.vers)

    if hasattr(hook_info, "compat"):
        spec = packaging.specifiers.SpecifierSet(hook_info.compat)

        if client_version not in spec:
            return False

    return True


def load_hooks(client: object) -> object:
    """
    Loads hooks from the default hooks directory and returns the modified client
    """
    hook_dir = os.path.join(os.getenv("APPDATA"), "hcclient", "hooks") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient", "hooks")
    if not os.path.isdir(hook_dir):
        return client

    for hook in os.listdir(hook_dir):
        if hook.endswith(".py"):
            try:
                hook_path = os.path.join(hook_dir, hook)
                spec = importlib.util.spec_from_file_location(hook, hook_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if not check_hook(module):
                    print(f"{sys.argv[0]}: warning: skipping hook '{hook}' due to missing or invalid HookInfo class")
                    continue

                if not check_compat(module.HookInfo):
                    print(f"{sys.argv[0]}: warning: skipping hook '{module.HookInfo.name}' due to incompatible version (requires: {module.HookInfo.compat}, client: {meta.vers})")
                    continue

                client = module.hook(client)
                client.hooks.append(f"{module.HookInfo.name}[{module.HookInfo.version}]")

            except Exception as e:
                sys.exit(f"{sys.argv[0]}: error: unable to load hook '{hook}': {e}")

    return client
