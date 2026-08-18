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


SAMPLE_PRD = """# 러닝 크루 PRD

> **AI 에이전트에게:** 이 문서는 구현 지침입니다.

## 1. 개요
동네 러닝 크루의 기록을 남긴다.

## 4. Non-Goals (하지 않는 것)
- 이번 버전에서 결제는 구현하지 않는다.
- 이번 버전에서 소셜 로그인은 구현하지 않는다.
- 이번 버전에서 푸시 알림은 구현하지 않는다. (가정)

## 6. 페이즈별 요구사항

### Phase 1: 기본 동작
**목표:** 기록을 저장한다
**요구사항:**
1. 기록을 입력한다
2. 기록을 저장한다
**수용 기준:**
- [ ] 기록 저장 후 목록에 보인다
- [x] 앱이 실행된다

### Phase 2: 확장 (Phase 1의 저장소 필요)
**목표:** 공유한다
**요구사항:**
1. 링크를 만든다
**수용 기준:**
- [ ] 링크로 기록이 열린다
"""


class TestStructureParsing(unittest.TestCase):
    def stripped(self, text=SAMPLE_PRD):
        from validate_prd import strip_fenced_blocks

        return strip_fenced_blocks(text.splitlines())

    def test_detect_lang_korean(self):
        self.assertEqual(p.detect_lang("한국어 문서입니다"), "ko")

    def test_detect_lang_english(self):
        self.assertEqual(p.detect_lang("This is an English PRD"), "en")

    def test_extract_title(self):
        self.assertEqual(
            p.extract_title(SAMPLE_PRD.splitlines(), "PRD"), "러닝 크루 PRD"
        )

    def test_extract_title_falls_back(self):
        self.assertEqual(p.extract_title(["본문뿐"], "PRD"), "PRD")

    def test_collect_non_goals(self):
        goals = p.collect_non_goals(self.stripped())
        self.assertEqual(len(goals), 3)
        self.assertIn("결제", goals[0])

    def test_collect_phases_counts(self):
        phases = p.collect_phases(self.stripped())
        self.assertEqual(len(phases), 2)
        self.assertEqual(len(phases[0]["requirements"]), 2)
        self.assertEqual(len(phases[0]["criteria"]), 2)

    def test_requirement_ids(self):
        phases = p.collect_phases(self.stripped())
        self.assertEqual(phases[0]["requirements"][1]["id"], "P1-R2")
        self.assertEqual(phases[1]["requirements"][0]["anchor"], "p2-r1")

    def test_criteria_ids_and_checked_state(self):
        crits = p.collect_phases(self.stripped())[0]["criteria"]
        self.assertEqual(crits[0]["id"], "P1-A1")
        self.assertFalse(crits[0]["checked"])
        self.assertTrue(crits[1]["checked"])

    def test_phase_notes_captured(self):
        notes = p.collect_phases(self.stripped())[0]["notes"]
        self.assertTrue(any("목표" in x for x in notes))

    def test_fenced_examples_do_not_create_phantom_phases(self):
        text = "## 6. 요구사항\n\n```\n### Phase 9: 가짜\n- [ ] 가짜 기준\n```\n"
        self.assertEqual(p.collect_phases(self.stripped(text)), [])

    def test_split_sections(self):
        chunks = p.split_sections(SAMPLE_PRD.splitlines())
        nums = [c["num"] for c in chunks]
        self.assertEqual(nums[0], None)
        self.assertIn(1, nums)
        self.assertIn(6, nums)


if __name__ == "__main__":
    unittest.main()
