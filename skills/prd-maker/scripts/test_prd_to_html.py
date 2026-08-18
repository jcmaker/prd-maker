"""Tests for prd_to_html.py — the deterministic PRD-to-HTML converter.

Run with: cd skills/prd-maker/scripts && python3 test_prd_to_html.py
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

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


class TestDocumentAssembly(unittest.TestCase):
    def build(self, text=SAMPLE_PRD):
        doc = p.parse_document(text, "PRD")
        return p.render_document(doc, "PRD.md", "2026-08-18 12:00")

    def test_has_lang_attribute(self):
        self.assertIn('<html lang="ko"', self.build())

    def test_title_ignores_headings_inside_code_fences(self):
        doc = p.parse_document("```\n# 예시 제목\n```\n\n# 진짜 제목\n", "PRD")
        self.assertEqual(doc["title"], "진짜 제목")

    def test_dashboard_has_one_tile_per_metric(self):
        html = self.build()
        self.assertIn('class="dash"', html)
        # phases, requirements, criteria, non-goals, assumptions
        self.assertEqual(html.count('class="tile'), 5)

    def test_assumption_panel_lists_every_assumption(self):
        doc = p.parse_document(SAMPLE_PRD, "PRD")
        html = p.render_document(doc, "PRD.md", "t")
        self.assertEqual(len(doc["assumptions"]), 1)
        self.assertIn('id="assumptions"', html)
        panel = html.split('id="assumptions"', 1)[1].split("</section>", 1)[0]
        self.assertIn("푸시 알림", panel)

    def test_assumption_panel_absent_when_no_assumptions(self):
        doc = p.parse_document("# 메모\n\n확인되지 않은 내용 없음.\n", "메모")
        self.assertEqual(doc["assumptions"], [])
        self.assertNotIn('id="assumptions"', p.render_document(doc, "memo.md", "t"))

    def test_requirement_anchors_exist(self):
        html = self.build()
        self.assertIn('id="p1-r1"', html)
        self.assertIn('id="p1-a1"', html)

    def test_requirement_index_table_present(self):
        self.assertIn("req-index", self.build())

    def test_footer_states_derived_status(self):
        self.assertIn("PRD.md", self.build())

    def test_print_and_dark_css_present(self):
        html = self.build()
        self.assertIn("@media print", html)
        self.assertIn("prefers-color-scheme", html)

    def test_korean_typography_rules_present(self):
        self.assertIn("keep-all", self.build())

    def test_no_external_resources(self):
        html = self.build()
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link href=", html)
        self.assertNotIn("@import", html)

    def test_partial_enhancement_drops_missing_pieces(self):
        html = p.render_document(
            p.parse_document("# 그냥 메모\n\n본문 한 줄.\n", "메모"), "memo.md", "t"
        )
        self.assertIn("그냥 메모", html)
        self.assertNotIn("req-index", html)
        self.assertNotIn('id="p1-r1"', html)


SCRIPT_PATH = pathlib.Path(__file__).parent / "prd_to_html.py"
EXAMPLES = pathlib.Path(__file__).resolve().parents[3] / "docs" / "examples"


def run_cli(args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)] + args,
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, result.stdout + result.stderr


class TestCLI(unittest.TestCase):
    def write_tmp(self, text, suffix=".md"):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        )
        f.write(text)
        f.close()
        self.addCleanup(lambda: pathlib.Path(f.name).unlink(missing_ok=True))
        return pathlib.Path(f.name)

    def test_writes_sibling_html_file(self):
        src = self.write_tmp(SAMPLE_PRD)
        code, out = run_cli([str(src)])
        self.assertEqual(code, 0, out)
        target = src.with_suffix(".html")
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.assertTrue(target.is_file())

    def test_output_flag(self):
        src = self.write_tmp(SAMPLE_PRD)
        dest = pathlib.Path(tempfile.gettempdir()) / "prd_to_html_out.html"
        self.addCleanup(lambda: dest.unlink(missing_ok=True))
        code, out = run_cli([str(src), "--output", str(dest)])
        self.assertEqual(code, 0, out)
        self.assertIn("러닝 크루", dest.read_text(encoding="utf-8"))

    def test_missing_argument_exits_2(self):
        code, out = run_cli([])
        self.assertEqual(code, 2)
        self.assertIn("Usage", out)

    def test_missing_file_exits_2(self):
        self.assertEqual(run_cli(["/no/such/PRD.md"])[0], 2)

    def test_non_utf8_exits_2(self):
        f = tempfile.NamedTemporaryFile(mode="wb", suffix=".md", delete=False)
        f.write("# 제목\n".encode("euc-kr"))
        f.close()
        self.addCleanup(lambda: pathlib.Path(f.name).unlink(missing_ok=True))
        code, out = run_cli([f.name])
        self.assertEqual(code, 2)
        self.assertIn("UTF-8", out)

    def test_empty_file_still_produces_html(self):
        src = self.write_tmp("")
        target = src.with_suffix(".html")
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.assertEqual(run_cli([str(src)])[0], 0)
        self.assertIn("<html", target.read_text(encoding="utf-8"))


class TagBalance(HTMLParser):
    """Fails on unbalanced or mis-nested tags.

    `HTMLParser` alone accepts almost anything — it recovers silently from
    unclosed and mismatched tags — so feeding it the output only proves the
    generator did not raise. This subclass tracks the open-tag stack, which is
    what "well-formed" in spec section 7 actually means.
    """

    VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append("</%s> with nothing open" % tag)
        elif self.stack[-1] != tag:
            self.errors.append("expected </%s>, got </%s>" % (self.stack[-1], tag))
        else:
            self.stack.pop()


class TestSpecAcceptance(unittest.TestCase):
    """The six checks named in section 7 of the design spec."""

    def convert(self, path):
        text = pathlib.Path(path).read_text(encoding="utf-8")
        doc = p.parse_document(text, pathlib.Path(path).stem)
        return doc, p.render_document(doc, pathlib.Path(path).name, "t")

    def test_1_examples_are_well_formed(self):
        files = sorted(EXAMPLES.glob("*.md"))
        self.assertTrue(files, "docs/examples/*.md not found")
        for f in files:
            _, html = self.convert(f)
            checker = TagBalance()
            checker.feed(html)
            checker.close()
            self.assertEqual(checker.errors, [], f.name)
            self.assertEqual(checker.stack, [], "%s: unclosed %s" % (f.name, checker.stack))

    def test_2_self_contained(self):
        for f in sorted(EXAMPLES.glob("*.md")):
            _, html = self.convert(f)
            self.assertNotIn("<script src=", html)
            self.assertNotIn("<link href=", html)
            self.assertNotIn("@import", html)
            self.assertNotIn('src="http', html)

    def test_3_assumption_count_matches_linter(self):
        from validate_prd import find_assumptions, strip_fenced_blocks

        for f in sorted(EXAMPLES.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            expected = len(find_assumptions(strip_fenced_blocks(text.splitlines())))
            doc, _ = self.convert(f)
            self.assertEqual(len(doc["assumptions"]), expected, f.name)

    def test_4_script_input_is_neutralized(self):
        doc = p.parse_document("# T\n\n<script>alert(1)</script>\n", "T")
        html = p.render_document(doc, "T.md", "t")
        body = html.split("<main", 1)[1]
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_5_arbitrary_markdown_converts(self):
        doc = p.parse_document("# 회의록\n\n- 항목 하나\n- 항목 둘\n", "회의록")
        html = p.render_document(doc, "notes.md", "t")
        self.assertIn("회의록", html)
        # the body must survive, not just the title
        self.assertIn("항목 하나", html)
        self.assertIn("항목 둘", html)
        self.assertNotIn("req-index", html)

    def test_6_print_and_dark_css(self):
        _, html = self.convert(sorted(EXAMPLES.glob("*.md"))[0])
        self.assertIn("@media print", html)
        self.assertIn("prefers-color-scheme", html)


if __name__ == "__main__":
    unittest.main()
