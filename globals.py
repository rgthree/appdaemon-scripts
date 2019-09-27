import secrets
import random

def get_arg(args, key, allow_empty=False, default_value=None):
    if not key in args and allow_empty:
        return default_value

    key = args[key]
    if type(key) is str and key.startswith("secret_"):
        if key in secrets.secret_dict:
            return secrets.secret_dict[key]
        else:
            raise KeyError("Could not find {} in secret_dict".format(key))
    else:
        return key


def get_arg_list(args, key, allow_empty=False):
    arg_list = []
    if not key in args and allow_empty:
        return arg_list

    if isinstance(args[key], list):
        arg = args[key]
    else:
        arg = (args[key]).split(",")
    for key in arg:
        if type(key) is str and key.startswith("secret_"):
            if key in secrets.secret_dict:
                arg_list.append(secrets.secret_dict[key])
            else:
                raise KeyError("Could not find {} in secret_dict".format(key))
        else:
            arg_list.append(key)
    return arg_list
