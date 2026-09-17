from django.http import HttpResponse


def htmx_redirect(url: str) -> HttpResponse:
    """204 response with HX-Redirect; tells HTMX to client-side redirect."""
    response = HttpResponse(status=204)
    response["HX-Redirect"] = url
    return response
