"""Tests for prd_to_html.py — the deterministic PRD-to-HTML converter.

Run with: cd skills/prd-maker/scripts && python3 test_prd_to_html.py
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import prd_to_html as p


class TestEscape(unittest.TestCase):
    def test_escapes_html_metacharacters(self):
        self.assertEqual(p.escape("a & b"), "a &amp; b")
        self.assertEqual(p.escape("<b>"), "&lt;b&gt;")
        self.assertEqual(p.escape('say "hi"'), "say &quot;hi&quot;")

    def test_ampersand_escaped_first(self):
        self.assertEqual(p.escape("<"), "&lt;")


class TestRenderInline(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(p.render_inline("a **b** c"), "a <strong>b</strong> c")

    def test_inline_code(self):
        self.assertEqual(p.render_inline("run `ls -l`"), "run <code>ls -l</code>")

    def test_link_with_safe_scheme(self):
        self.assertEqual(
            p.render_inline("[docs](https://example.com)"),
            '<a href="https://example.com">docs</a>',
        )

    def test_relative_and_anchor_links_allowed(self):
        self.assertIn('href="#s1"', p.render_inline("[a](#s1)"))
        self.assertIn('href="./PRD.md"', p.render_inline("[a](./PRD.md)"))

    def test_javascript_url_is_not_rendered_as_link(self):
        out = p.render_inline("[click](javascript:alert(1))")
        self.assertNotIn("<a ", out)
        self.assertIn("[click]", out)  # left as inert text, not a link

    def test_raw_html_is_escaped_not_rendered(self):
        out = p.render_inline("<script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


if __name__ == "__main__":
    unittest.main()
