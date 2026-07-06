"""Tests for validate_prd.py — the deterministic PRD structure linter.

Run with: cd skills/prd-maker/scripts && python3 test_validate_prd.py
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).parent / "validate_prd.py"


def run_validator(text):
    """Write `text` to a temp file and run validate_prd.py against it.

    Returns (returncode, stdout).
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        path = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), path],
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr
    finally:
        pathlib.Path(path).unlink()


VALID_PRD = """# 러닝 크루 PRD

> **AI 에이전트에게:** 이 문서는 구현 지침입니다. 불명확한 부분은 추측하지 마세요.

## 1. 개요
문제와 목표 2~3문장.

## 2. 대상 사용자 & JTBD
누가, 어떤 상황에서, 무엇을 이루려고.

## 3. 핵심 기능 (스코프)
1. **기능 A** — 설명
2. **기능 B** — 설명

## 4. Non-Goals (하지 않는 것)
- 이번 버전에서 결제는 구현하지 않는다.
- 이번 버전에서 소셜 로그인은 구현하지 않는다.
- 이번 버전에서 푸시 알림은 구현하지 않는다.

## 5. 기술 제약 & 기존 결정
- 로컬 저장 — 혼자 쓰는 도구이므로 (가정)

## 6. 페이즈별 요구사항

### Phase 1: 기본 동작
**목표:** 동작 확인
**요구사항:**
1. 요구사항 1
2. 요구사항 2
**수용 기준:**
- [ ] 기준 1

### Phase 2: 확장 (Phase 1의 저장소 필요)
**목표:** 확장 기능 제공
**요구사항:**
1. 요구사항 1
**수용 기준:**
- [x] 기준 1

## 7. 성공 지표
- 지표 1 (가정)
"""


def make_valid_prd():
    return VALID_PRD


class TestValidPrd(unittest.TestCase):
    def test_valid_prd_passes_all_checks(self):
        code, out = run_validator(make_valid_prd())
        self.assertEqual(code, 0, msg=out)
        self.assertNotIn("FAIL", out)
        self.assertIn("PASS", out)


class TestCheck1Header(unittest.TestCase):
    def test_missing_blockquote_header_fails(self):
        text = make_valid_prd().replace(
            "> **AI 에이전트에게:** 이 문서는 구현 지침입니다. 불명확한 부분은 추측하지 마세요.\n",
            "",
        )
        code, out = run_validator(text)
        self.assertEqual(code, 1)
        self.assertIn("CHECK 1", out)
        check1_line = [l for l in out.splitlines() if "CHECK 1" in l][0]
        self.assertIn("FAIL", check1_line)

    def test_blockquote_too_late_fails(self):
        # Push the blockquote past the first 5 non-empty lines.
        filler = "\n".join(f"필러 라인 {i}" for i in range(1, 6))
        text = make_valid_prd().replace(
            "# 러닝 크루 PRD\n\n> **AI 에이전트에게:**",
            f"# 러닝 크루 PRD\n\n{filler}\n\n> **AI 에이전트에게:**",
        )
        code, out = run_validator(text)
        self.assertEqual(code, 1)
        self.assertTrue(
            "FAIL" in out and "CHECK 1" in out,
            msg=out,
        )


class TestFencedCodeBlocks(unittest.TestCase):
    def test_fenced_heading_and_assumption_are_ignored(self):
        # A fenced markdown example containing `## 3.` must not trip CHECK 2,
        # and a `(가정)` line inside the fence must not be listed.
        fenced = (
            "예시:\n"
            "```markdown\n"
            "## 3. 펜스 안 가짜 섹션\n"
            "- 펜스 안 항목 (가정)\n"
            "```\n"
        )
        text = make_valid_prd().replace(
            "## 5. 기술 제약 & 기존 결정\n",
            "## 5. 기술 제약 & 기존 결정\n" + fenced,
        )
        code, out = run_validator(text)
        self.assertEqual(code, 0, msg=out)
        check2_line = [l for l in out.splitlines() if "CHECK 2" in l][0]
        self.assertIn("PASS", check2_line)
        self.assertIn("ASSUMPTIONS (2):", out)


class TestCheck2Sections(unittest.TestCase):
    def test_out_of_order_only_fails(self):
        # All 7 sections present exactly once, but sections 2 and 3 swapped.
        text = make_valid_prd()
        lines = text.splitlines(keepends=True)
        s2 = next(i for i, l in enumerate(lines) if l.startswith("## 2."))
        s3 = next(i for i, l in enumerate(lines) if l.startswith("## 3."))
        s4 = next(i for i, l in enumerate(lines) if l.startswith("## 4."))
        swapped = lines[:s2] + lines[s3:s4] + lines[s2:s3] + lines[s4:]
        code, out = run_validator("".join(swapped))
        self.assertEqual(code, 1)
        check2_line = [l for l in out.splitlines() if "CHECK 2" in l][0]
        self.assertIn("FAIL", check2_line)
        self.assertIn("order", check2_line)

    def test_missing_section_fails(self):
        text = make_valid_prd()
        # Remove section 4 entirely (heading through the line before section 5).
        lines = text.splitlines(keepends=True)
        start = next(i for i, l in enumerate(lines) if l.startswith("## 4."))
        end = next(i for i, l in enumerate(lines) if l.startswith("## 5."))
        new_text = "".join(lines[:start] + lines[end:])
        code, out = run_validator(new_text)
        self.assertEqual(code, 1)
        self.assertIn("CHECK 2", out)
        check2_line = [l for l in out.splitlines() if "CHECK 2" in l][0]
        self.assertIn("FAIL", check2_line)

    def test_duplicated_section_fails(self):
        text = make_valid_prd()
        text = text.replace(
            "## 7. 성공 지표",
            "## 3. 중복 섹션",  # duplicate section number 3
            1,
        )
        code, out = run_validator(text)
        self.assertEqual(code, 1)
        check2_line = [l for l in out.splitlines() if "CHECK 2" in l][0]
        self.assertIn("FAIL", check2_line)


class TestCheck3NonGoals(unittest.TestCase):
    def test_only_two_non_goals_fails(self):
        text = make_valid_prd().replace(
            "- 이번 버전에서 푸시 알림은 구현하지 않는다.\n", ""
        )
        code, out = run_validator(text)
        self.assertEqual(code, 1)
        check3_line = [l for l in out.splitlines() if "CHECK 3" in l][0]
        self.assertIn("FAIL", check3_line)
        self.assertIn("2", check3_line)


class TestCheck4PhasesCheckboxes(unittest.TestCase):
    def test_section_6_without_any_phase_heading_fails(self):
        text = make_valid_prd()
        lines = text.splitlines(keepends=True)
        s6 = next(i for i, l in enumerate(lines) if l.startswith("## 6."))
        s7 = next(i for i, l in enumerate(lines) if l.startswith("## 7."))
        # Replace section 6's body with phase-less content.
        new_body = "요구사항이 phase 없이 나열됨.\n- [ ] 기준 1\n\n"
        new_text = "".join(lines[: s6 + 1]) + new_body + "".join(lines[s7:])
        code, out = run_validator(new_text)
        self.assertEqual(code, 1)
        check4_line = [l for l in out.splitlines() if "CHECK 4" in l][0]
        self.assertIn("FAIL", check4_line)

    def test_phase_without_checkbox_fails(self):
        text = make_valid_prd().replace(
            "**수용 기준:**\n- [x] 기준 1\n", "**수용 기준:**\n(없음)\n"
        )
        code, out = run_validator(text)
        self.assertEqual(code, 1)
        check4_line = [l for l in out.splitlines() if "CHECK 4" in l][0]
        self.assertIn("FAIL", check4_line)
        self.assertIn("Phase 2", check4_line)


class TestCheck5RequirementsCap(unittest.TestCase):
    def test_51_requirements_in_phase_fails(self):
        many_reqs = "\n".join(f"{i}. 요구사항 {i}" for i in range(1, 52))
        text = make_valid_prd().replace(
            "**요구사항:**\n1. 요구사항 1\n2. 요구사항 2\n**수용 기준:**\n- [ ] 기준 1",
            f"**요구사항:**\n{many_reqs}\n**수용 기준:**\n- [ ] 기준 1",
        )
        code, out = run_validator(text)
        self.assertEqual(code, 1)
        check5_line = [l for l in out.splitlines() if "CHECK 5" in l][0]
        self.assertIn("FAIL", check5_line)
        self.assertIn("Phase 1", check5_line)
        self.assertIn("51", check5_line)


class TestAssumptions(unittest.TestCase):
    def test_korean_and_english_assumption_markers_are_both_counted(self):
        text = make_valid_prd().replace(
            "- 지표 1 (가정)", "- 지표 1 (가정)\n- Metric 2 (assumption)"
        )
        code, out = run_validator(text)
        self.assertEqual(code, 0, msg=out)
        self.assertIn("ASSUMPTIONS (3):", out)

    def test_no_assumptions_reports_zero(self):
        text = make_valid_prd().replace(" (가정)", "")
        code, out = run_validator(text)
        self.assertEqual(code, 0, msg=out)
        self.assertIn("ASSUMPTIONS (0):", out)


class TestCliUsage(unittest.TestCase):
    def test_no_argument_exits_2(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)

    def test_missing_file_exits_2(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "/no/such/file/PRD.md"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)

    def test_error_messages_go_to_stderr(self):
        no_arg = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True
        )
        self.assertEqual(no_arg.stdout, "")
        self.assertIn("Usage", no_arg.stderr)
        missing = subprocess.run(
            [sys.executable, str(SCRIPT), "/no/such/file/PRD.md"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(missing.stdout, "")
        self.assertNotEqual(missing.stderr, "")

    def test_non_utf8_file_exits_2(self):
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".md", delete=False
        ) as f:
            f.write("# 제목\n> 헤더\n".encode("euc-kr"))
            path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), path],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("UTF-8", result.stderr)
        finally:
            pathlib.Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
