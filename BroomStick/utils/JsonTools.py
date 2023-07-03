def flatten_dict(d, parent_key='', sep='.', max_depth=1, current_depth=0):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict) and (max_depth is None or current_depth < max_depth):
            items.extend(flatten_dict(v, new_key, sep=sep, max_depth=max_depth, current_depth=current_depth+1).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d, separator='.', max_depth=1, current_depth=0):
    output = {}
    for key, value in d.items():
        parts = key.split(separator)
        if max_depth and current_depth >= max_depth:
            output[parts[-1]] = value
            continue
        d = output
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return output