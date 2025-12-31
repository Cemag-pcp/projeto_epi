from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr_path):
    value = obj
    for part in attr_path.split("."):
        value = getattr(value, part, "")
        if callable(value):
            value = value()
    return value


@register.simple_tag
def nav_active(request, path_prefix):
    if request.path.startswith(path_prefix):
        return "active"
    return ""


@register.filter
def startswith(value, prefix):
    if value is None:
        return False
    return str(value).startswith(str(prefix))
