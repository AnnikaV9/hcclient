# Author:    AnnikaV9
# License:   Unlicense
# Version:   1.18.2-git

import os
import sys
import importlib

from hcclient.client import Client


def load_hooks(client: Client) -> Client:
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
                client = module.hook(client)

            except Exception as e:
                sys.exit(f"{sys.argv[0]}: error: Unable to load hook '{hook}': {e}")

    return client
