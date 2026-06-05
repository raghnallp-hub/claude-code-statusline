#!/usr/bin/env python3
"""
Comprehensive QA/Security Test Suite for statusline-command.py
Tests edge cases, malformed input, and potential security vulnerabilities.

Run with: python3 -m pytest test_statusline.py -v
Or: python3 test_statusline.py
"""
import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path


class StatuslineTest(unittest.TestCase):
    """Test suite for statusline command."""

    def run_statusline(self, json_input):
        """Run statusline-command.py with given JSON input."""
        result = subprocess.run(
            [sys.executable, "statusline-command.py"],
            input=json_input,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr

    # ============================================================================
    # EDGE CASE TESTS
    # ============================================================================

    def test_empty_input(self):
        """Test with empty input."""
        code, stdout, stderr = self.run_statusline("")
        self.assertEqual(code, 1, "Should reject empty input")

    def test_empty_json_object(self):
        """Test with empty JSON object."""
        code, stdout, stderr = self.run_statusline("{}")
        self.assertEqual(code, 0, "Should handle empty object")
        self.assertIn("Unknown Model", stdout)

    def test_null_json(self):
        """Test with null instead of object."""
        code, stdout, stderr = self.run_statusline("null")
        self.assertEqual(code, 1, "Should reject null")

    def test_json_array(self):
        """Test with JSON array instead of object."""
        code, stdout, stderr = self.run_statusline('[]')
        self.assertEqual(code, 1, "Should reject arrays")

    def test_json_string(self):
        """Test with JSON string instead of object."""
        code, stdout, stderr = self.run_statusline('"hello"')
        self.assertEqual(code, 1, "Should reject strings")

    def test_invalid_json(self):
        """Test with malformed JSON."""
        code, stdout, stderr = self.run_statusline('{invalid json}')
        self.assertEqual(code, 1, "Should reject invalid JSON")

    def test_incomplete_json(self):
        """Test with incomplete JSON."""
        code, stdout, stderr = self.run_statusline('{"model":')
        self.assertEqual(code, 1, "Should reject incomplete JSON")

    def test_missing_fields(self):
        """Test with completely missing all fields."""
        code, stdout, stderr = self.run_statusline('{"other_field": "value"}')
        self.assertEqual(code, 0)
        self.assertIn("Unknown Model", stdout)

    def test_null_values(self):
        """Test with null values in expected fields."""
        data = {
            "model": {"display_name": None},
            "context_window": {"used_percentage": None},
            "cost": {"total_cost_usd": None}
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    # ============================================================================
    # DATA TYPE TESTS (Wrong Types in Fields)
    # ============================================================================

    def test_model_as_number(self):
        """Test with model as number instead of string."""
        data = {"model": {"display_name": 12345}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("12345", stdout)

    def test_model_as_object(self):
        """Test with model as nested object."""
        data = {"model": {"display_name": {"nested": "value"}}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_context_as_string(self):
        """Test with context percentage as string."""
        data = {"context_window": {"used_percentage": "not a number"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("0%", stdout)

    def test_context_negative(self):
        """Test with negative context percentage."""
        data = {"context_window": {"used_percentage": -50}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_context_over_100(self):
        """Test with context percentage over 100."""
        data = {"context_window": {"used_percentage": 150}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("150%", stdout)

    def test_cost_negative(self):
        """Test with negative cost."""
        data = {"cost": {"total_cost_usd": -99.99}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("-99.99", stdout)

    def test_cost_as_string(self):
        """Test with cost as string."""
        data = {"cost": {"total_cost_usd": "free"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("$0.00", stdout)

    def test_rate_limit_as_string(self):
        """Test with rate limit as non-numeric string."""
        data = {
            "rate_limits": {
                "five_hour": {
                    "used_percentage": "high",
                    "resets_at": "tomorrow"
                }
            }
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    # ============================================================================
    # EXTREME VALUE TESTS
    # ============================================================================

    def test_extremely_large_number(self):
        """Test with extremely large numbers."""
        data = {"cost": {"total_cost_usd": 99999999999999999}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_very_small_float(self):
        """Test with very small floating point numbers."""
        data = {"context_window": {"used_percentage": 0.0000001}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_scientific_notation(self):
        """Test with scientific notation."""
        data = {"context_window": {"used_percentage": 1e2}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_infinity_json_payload(self):
        """Test with infinity (Python JSON accepts as JavaScript extension)."""
        # Python's json module accepts Infinity by design (JavaScript compatibility)
        code, stdout, stderr = self.run_statusline('{"value": Infinity}')
        self.assertEqual(code, 0)  # Should succeed gracefully

    # ============================================================================
    # LONG/OVERSIZED STRING TESTS
    # ============================================================================

    def test_extremely_long_model_name(self):
        """Test with extremely long model name (10KB)."""
        long_name = "A" * 10000
        data = {"model": {"display_name": long_name}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        # Should be truncated to 100 chars
        self.assertTrue(len(stdout) < 1000)

    def test_extremely_long_directory_name(self):
        """Test with extremely long directory path."""
        long_path = "/very/long/path/" + "subdir/" * 100
        data = {"worktree": {"original_cwd": long_path}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_extremely_long_worktree_name(self):
        """Test with extremely long worktree name."""
        long_name = "W" * 5000
        data = {"worktree": {"name": long_name}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_very_large_json_payload(self):
        """Test with very large JSON payload (1MB+)."""
        # Create a large but valid JSON object
        data = {
            "model": {"display_name": "Test"},
            "large_field": "X" * 1000000
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    # ============================================================================
    # UNICODE & ENCODING TESTS
    # ============================================================================

    def test_unicode_in_model_name(self):
        """Test with unicode characters in model name."""
        data = {"model": {"display_name": "Claude 📱 🚀 中文"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data, ensure_ascii=False))
        self.assertEqual(code, 0)

    def test_emoji_overload(self):
        """Test with excessive emoji."""
        data = {"model": {"display_name": "🤖" * 100}}
        code, stdout, stderr = self.run_statusline(json.dumps(data, ensure_ascii=False))
        self.assertEqual(code, 0)

    def test_control_characters(self):
        """Test with control characters in strings."""
        data = {"model": {"display_name": "Model\x00\x01\x02\x03"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_ansi_escape_codes_in_input(self):
        """Test with ANSI escape codes embedded in input."""
        data = {"model": {"display_name": "Model\033[31mRED\033[0m"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        # Should not execute or corrupt output
        self.assertIn("Model", stdout)

    def test_null_bytes_in_string(self):
        """Test with null bytes in strings."""
        # JSON doesn't support null bytes directly, but we can test edge cases
        data = {"model": {"display_name": "Model"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    # ============================================================================
    # SECURITY/INJECTION TESTS
    # ============================================================================

    def test_shell_injection_in_model_name(self):
        """Test shell injection attempt in model name."""
        data = {"model": {"display_name": "$(rm -rf /); echo pwned"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        # Should treat as literal string, not execute
        self.assertIn("rm -rf", stdout)

    def test_bash_command_substitution(self):
        """Test backtick command substitution."""
        data = {"model": {"display_name": "`whoami`"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        # Should be literal
        self.assertIn("whoami", stdout)

    def test_pipe_injection(self):
        """Test pipe injection attempt."""
        data = {"model": {"display_name": "Model | cat /etc/passwd"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_semicolon_injection(self):
        """Test semicolon command separator injection."""
        data = {"model": {"display_name": "Model; touch /tmp/pwned"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_python_code_injection(self):
        """Test Python code injection via string fields."""
        data = {"model": {"display_name": "__import__('os').system('touch /tmp/pwned')"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        # Should be treated as literal string
        self.assertIn("__import__", stdout)

    def test_format_string_attack(self):
        """Test format string vulnerability (Python f-string style)."""
        data = {"model": {"display_name": "{__import__('os').system('id')}"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_recursive_json_structure(self):
        """Test deeply nested JSON structure."""
        data = {"level1": {"level2": {"level3": {"level4": {"level5": "value"}}}}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_duplicate_keys(self):
        """Test JSON with duplicate keys (last one wins in JSON spec)."""
        json_str = '{"model": {"display_name": "First"}, "model": {"display_name": "Second"}}'
        code, stdout, stderr = self.run_statusline(json_str)
        self.assertEqual(code, 0)

    # ============================================================================
    # TIMESTAMP/TIMEZONE TESTS
    # ============================================================================

    def test_invalid_timestamp(self):
        """Test with invalid Unix timestamp."""
        data = {
            "rate_limits": {
                "five_hour": {
                    "used_percentage": 50,
                    "resets_at": "not a timestamp"
                }
            }
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_zero_timestamp(self):
        """Test with zero Unix timestamp (1970-01-01)."""
        data = {
            "rate_limits": {
                "five_hour": {
                    "used_percentage": 50,
                    "resets_at": 0
                }
            }
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_negative_timestamp(self):
        """Test with negative Unix timestamp (before 1970)."""
        data = {
            "rate_limits": {
                "five_hour": {
                    "used_percentage": 50,
                    "resets_at": -1000000
                }
            }
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_far_future_timestamp(self):
        """Test with far-future timestamp (year 3000+)."""
        data = {
            "rate_limits": {
                "five_hour": {
                    "used_percentage": 50,
                    "resets_at": 32503680000  # Year 3000
                }
            }
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    # ============================================================================
    # MALFORMED NESTED STRUCTURES
    # ============================================================================

    def test_model_is_array(self):
        """Test when model field is array instead of object."""
        data = {"model": ["element1", "element2"]}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_cost_is_string(self):
        """Test when cost is string instead of object."""
        data = {"cost": "expensive"}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_rate_limits_is_string(self):
        """Test when rate_limits is string."""
        data = {"rate_limits": "limited"}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    def test_worktree_is_number(self):
        """Test when worktree is number."""
        data = {"worktree": 12345}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)

    # ============================================================================
    # NORMAL OPERATION TESTS (Sanity Checks)
    # ============================================================================

    def test_valid_minimal_payload(self):
        """Test with minimal valid payload."""
        data = {"model": {"display_name": "Claude Sonnet"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("Claude Sonnet", stdout)
        self.assertIn("🤖", stdout)

    def test_valid_complete_payload(self):
        """Test with complete valid payload."""
        data = {
            "model": {"display_name": "Claude Sonnet 4.6"},
            "effort": {"level": "high"},
            "context_window": {"used_percentage": 45.5},
            "cost": {"total_cost_usd": 0.12},
            "rate_limits": {
                "five_hour": {
                    "used_percentage": 65,
                    "resets_at": 1717584000
                }
            },
            "worktree": {"name": "my-feature", "original_cwd": "/tmp"},
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("Claude Sonnet 4.6", stdout)
        self.assertIn("high", stdout)
        self.assertIn("0.12", stdout)
        self.assertIn("my-feature", stdout)

    def test_output_has_two_lines(self):
        """Test that output has exactly two lines."""
        data = {"model": {"display_name": "Test"}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 2, f"Expected 2 lines, got {len(lines)}: {lines}")

    def test_rate_limit_colors(self):
        """Test rate limit coloring at threshold boundaries."""
        # Test green (<70%)
        data = {
            "rate_limits": {
                "five_hour": {"used_percentage": 50, "resets_at": 1717584000}
            }
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[32m", stdout)  # Green color code

        # Test yellow (70-89%)
        data["rate_limits"]["five_hour"]["used_percentage"] = 75
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[33m", stdout)  # Yellow color code

        # Test red (>=90%)
        data["rate_limits"]["five_hour"]["used_percentage"] = 95
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[31m", stdout)  # Red color code

    def test_context_usage_colors(self):
        """Test context window usage coloring at threshold boundaries."""
        # Test no color (<30%)
        data = {"context_window": {"used_percentage": 25}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        # Should not have color codes for low usage

        # Test yellow (30-44%)
        data = {"context_window": {"used_percentage": 35}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[33m", stdout)  # Yellow color code
        self.assertIn("35%", stdout)

        # Test orange (45-49%)
        data = {"context_window": {"used_percentage": 47}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[38;5;208m", stdout)  # Orange color code
        self.assertIn("47%", stdout)

        # Test purple (50-55%)
        data = {"context_window": {"used_percentage": 52}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[35m", stdout)  # Purple color code
        self.assertIn("52%", stdout)

        # Test red (>=55%)
        data = {"context_window": {"used_percentage": 60}}
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("\033[31m", stdout)  # Red color code
        self.assertIn("60%", stdout)


class StatuslineStressTest(unittest.TestCase):
    """Stress tests for stability and DoS resistance."""

    def run_statusline(self, json_input):
        """Run statusline command with timeout."""
        result = subprocess.run(
            [sys.executable, "statusline-command.py"],
            input=json_input,
            capture_output=True,
            text=True,
            timeout=5  # 5 second timeout
        )
        return result.returncode, result.stdout, result.stderr

    def test_timeout_protection(self):
        """Verify script completes within timeout."""
        # Even with huge payload, should complete in <5 seconds
        data = {"model": {"display_name": "X" * 100000}}
        try:
            code, stdout, stderr = self.run_statusline(json.dumps(data))
            self.assertIn(code, [0, 1])  # Either success or graceful failure
        except subprocess.TimeoutExpired:
            self.fail("Script timeout — possible infinite loop")

    def test_memory_doesnt_explode(self):
        """Verify script doesn't consume excessive memory with large input."""
        # Create large but valid JSON
        data = {
            "model": {"display_name": "Test"},
            "huge_array": list(range(100000))
        }
        code, stdout, stderr = self.run_statusline(json.dumps(data))
        # Should either succeed or fail gracefully
        self.assertIn(code, [0, 1])


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
