from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def timeuntil(value, arg=None):
    """Calculate the time difference between two dates"""
    if not value:
        return ''
    
    if arg:
        try:
            delta = value - arg
        except:
            return ''
    else:
        delta = value
    
    if isinstance(delta, timedelta):
        # Convert to hours
        hours = delta.total_seconds() / 3600
        return f"{hours:.1f} hours"
    
    return ''

@register.filter
def ksh_currency(value):
    """Format value as Kenyan Shillings"""
    try:
        return f"KSH {float(value):,.0f}"
    except (ValueError, TypeError):
        return "KSH 0"

@register.filter
def ksh_currency_decimal(value):
    """Format value as Kenyan Shillings with decimals"""
    try:
        return f"KSH {float(value):,.2f}"
    except (ValueError, TypeError):
        return "KSH 0.00"
