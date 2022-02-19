def to_f(v):
    if isinstance(v, float):
        return '{:.2f}'.format(v).replace('.', ',')
    return str(v).replace('.', ',')


def to_f4(v):
    if isinstance(v, float):
        return '{:.4f}'.format(v).replace('.', ',')
    return str(v).replace('.', ',')
