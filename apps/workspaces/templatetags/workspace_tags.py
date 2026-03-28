import hashlib

from django import template

register = template.Library()

_COLORS = [
    "bg-red-500",
    "bg-orange-500",
    "bg-amber-500",
    "bg-lime-600",
    "bg-green-500",
    "bg-emerald-500",
    "bg-teal-500",
    "bg-cyan-600",
    "bg-sky-500",
    "bg-blue-500",
    "bg-indigo-500",
    "bg-violet-500",
    "bg-purple-600",
    "bg-fuchsia-600",
    "bg-pink-500",
    "bg-rose-500",
]


@register.filter
def workspace_color(name):
    """Return a Tailwind bg color class deterministically based on the workspace name."""
    if not name:
        return "bg-gray-500"
    digest = int(hashlib.md5(name.lower().encode()).hexdigest(), 16)
    return _COLORS[digest % len(_COLORS)]
