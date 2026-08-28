"""Views de renderização do frontend (servido pelo Django)."""

from django.shortcuts import render


def index(request):
    """Renderiza a aplicação Atlas (SPA em HTML/CSS/JS puro)."""
    return render(request, "atlas/index.html")
