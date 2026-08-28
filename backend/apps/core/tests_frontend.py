"""Testes do frontend servido pelo Django (HTML/CSS/JS puro)."""

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import resolve, reverse


class FrontendServeTests(TestCase):
    """FASE 1 — o frontend é entregue pelo Django (mesma origem)."""

    def test_index_route_resolves(self):
        match = resolve("/")
        self.assertEqual(match.func.__name__, "index")

    def test_index_template_uses_static_app(self):
        html = render_to_string("atlas/index.html")
        self.assertIn('id="app"', html)
        self.assertIn("atlas/js/app.js", html)
        self.assertIn("atlas/css/app.css", html)

    def test_static_files_exist(self):
        from pathlib import Path

        # Frontend separado em <repo>/frontend/static/atlas.
        backend = Path(__file__).resolve().parent.parent.parent
        base = backend.parent / "frontend" / "static" / "atlas"
        self.assertTrue((base / "css" / "app.css").exists())
        self.assertTrue((base / "js" / "app.js").exists())
        self.assertTrue((base / "js" / "api.js").exists())
        self.assertTrue((base / "js" / "auth.js").exists())
        self.assertTrue((base / "js" / "router.js").exists())
        self.assertTrue((base / "js" / "helpers.js").exists())
        self.assertTrue((base / "js" / "pages" / "auth.js").exists())
        self.assertTrue((base / "js" / "pages" / "app.js").exists())
        self.assertTrue((base / "js" / "pages" / "assistant.js").exists())
        self.assertTrue((base / "js" / "pages" / "entities.js").exists())
        self.assertTrue((base / "js" / "pages" / "settings.js").exists())
        self.assertTrue((backend.parent / "frontend" / "templates" / "atlas" / "index.html").exists())
