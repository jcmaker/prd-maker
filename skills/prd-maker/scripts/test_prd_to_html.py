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


class TestRenderBlocks(unittest.TestCase):
    def render(self, md):
        html, _ = p.render_blocks(md.splitlines())
        return html

    def test_headings_get_ids(self):
        html, headings = p.render_blocks(["## 1. 개요"])
        self.assertIn("<h2 id=", html)
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0][0], 2)

    def test_duplicate_headings_get_unique_ids(self):
        _, headings = p.render_blocks(["## 개요", "", "## 개요"])
        self.assertNotEqual(headings[0][2], headings[1][2])

    def test_unordered_list(self):
        html = self.render("- a\n- b")
        self.assertIn("<ul>", html)
        self.assertEqual(html.count("<li>"), 2)

    def test_ordered_list(self):
        html = self.render("1. first\n2. second")
        self.assertIn("<ol>", html)

    def test_checkbox_renders_marker_text_not_color_only(self):
        html = self.render("- [ ] 미완료\n- [x] 완료")
        self.assertIn("☐", html)
        self.assertIn("☑", html)

    def test_blockquote(self):
        self.assertIn("<blockquote>", self.render("> 에이전트에게"))

    def test_fenced_code_is_escaped(self):
        html = self.render("```\n<script>x</script>\n```")
        self.assertIn("<pre>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_table(self):
        html = self.render("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<table>", html)
        self.assertIn("<th>", html)
        self.assertIn("<td>", html)

    def test_paragraph(self):
        self.assertIn("<p>", self.render("그냥 문장입니다."))

    def test_unsupported_syntax_survives_as_text(self):
        html = self.render("~~취소선~~")
        self.assertIn("~~취소선~~", html)


if __name__ == "__main__":
    unittest.main()
