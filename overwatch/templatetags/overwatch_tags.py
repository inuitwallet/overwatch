from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def profit_render(value):
    if value > 0:
        rendered_value = '<span style="color: green">$ {:.2f}</span>'.format(value)
    elif value == 0:
        rendered_value = '<span>$ {:.2f}</span>'.format(value)
    else:
        rendered_value = '<span style="color: red">$ {:.2f}</span>'.format(value)

    return mark_safe(rendered_value)
