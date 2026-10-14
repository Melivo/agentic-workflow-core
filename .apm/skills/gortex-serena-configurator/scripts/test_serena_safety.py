#!/usr/bin/env python3
"""Unit tests for the Serena safety utility."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import serena_safety


class SerenaSafetyTests(unittest.TestCase):
    def test_writes_missing_playbook(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            agents = Path(temp) / "AGENTS.md"
            result = serena_safety.update_agents(agents, apply=True)
            text = agents.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "written")
            self.assertEqual(text.count(serena_safety.START), 1)
            self.assertIn("Use Gortex", text)
            self.assertIn("initialized, project-scoped Serena fallback", text)
            self.assertIn("native file and search tools only when neither Gortex nor Serena", text)
            self.assertIn("Serena/Gortex Code Intelligence Playbook", text)
            self.assertIn("native file, search, and runtime tools as the fallback instead of Gortex or Serena", text)

    def test_preserves_equivalent_existing_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            agents = Path(temp) / "AGENTS.md"
            original = (
                "## Serena/Gortex Code Intelligence Playbook\n\n"
                "Use Gortex first and an initialized project-scoped Serena fallback second. "
                "Use native file and search tools only when neither Gortex nor Serena can serve the operation. "
                "Never run broad Serena searches. Expand sequentially. After a timeout, use Serena CLI. "
                "When the CWD is Path.home(), use native file, search, and runtime tools as the fallback "
                "instead of Gortex or Serena. "
                "Use Serena CLI only for configuration, project management, memories, and recovery. "
                "Never configure or activate the user home or a filesystem root as a Serena project. "
                "Keep the effective global Serena metadata project at languages: []. "
                "Keep the global Serena MCP deprovisioned.\n"
            )
            agents.write_text(original, encoding="utf-8")
            result = serena_safety.update_agents(agents, apply=True)
            self.assertEqual(result["status"], "equivalent-existing")
            self.assertEqual(agents.read_text(encoding="utf-8"), original)

    def test_preserves_complete_unmanaged_serena_gortex_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            agents = Path(temp) / "AGENTS.md"
            original = serena_safety.PLAYBOOK.replace(f"{serena_safety.START}\n", "").replace(
                f"{serena_safety.END}\n", ""
            )
            agents.write_text(original, encoding="utf-8")
            result = serena_safety.update_agents(agents, apply=True)
            self.assertEqual(result["status"], "equivalent-existing")
            self.assertEqual(agents.read_text(encoding="utf-8"), original)

    def test_migrates_legacy_managed_block_without_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            agents = Path(temp) / "AGENTS.md"
            agents.write_text(
                f"Header\n\n{serena_safety.LEGACY_START}\nold\n{serena_safety.LEGACY_END}\n",
                encoding="utf-8",
            )
            result = serena_safety.update_agents(agents, apply=True)
            text = agents.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "written")
            self.assertEqual(text.count(serena_safety.START), 1)
            self.assertNotIn(serena_safety.LEGACY_START, text)
            self.assertNotIn("\nold\n", text)

    def test_replaces_managed_block_without_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            agents = Path(temp) / "AGENTS.md"
            agents.write_text(
                f"Header\n\n{serena_safety.START}\nold\n{serena_safety.END}\n",
                encoding="utf-8",
            )
            serena_safety.update_agents(agents, apply=True)
            text = agents.read_text(encoding="utf-8")
            self.assertEqual(text.count(serena_safety.START), 1)
            self.assertNotIn("\nold\n", text)

    def test_writes_missing_project_playbook(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agents = root / "AGENTS.md"
            result = serena_safety.update_project_agents(agents, apply=True, allowed_root=root)
            text = agents.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "written")
            self.assertEqual(text.count(serena_safety.PROJECT_START), 1)
            self.assertIn("Serena/Gortex Repository Code Intelligence", text)
            self.assertNotIn("Path.home()", text)

    def test_updates_existing_complete_global_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / ".serena" / "serena_config.yml"
            config.parent.mkdir()
            config.write_text("projects: []\ntool_timeout: 30.0\n", encoding="utf-8")
            result = serena_safety.set_global_timeout(config, apply=True)
            self.assertEqual(result["value"], 10.0)
            self.assertIn("tool_timeout: 10.0", config.read_text(encoding="utf-8"))

    def test_flags_project_tool_timeout_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project.yml"
            project.write_text("project_name: demo\ntool_timeout: 10\n", encoding="utf-8")
            result = serena_safety.inspect_project_config(project)
            self.assertEqual(result["status"], "unsupported-key")

    def test_reads_yaml_list_tool_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "servers.yaml"
            config.write_text(
                "serena:\n  timeout: 10000\n  command:\n    - serena\n    - --tool-timeout\n    - \"10\"\n",
                encoding="utf-8",
            )
            result = serena_safety.inspect_client_config(config)
            self.assertTrue(result["tool_timeout_10"])
            self.assertEqual(result["cli_tool_timeout"]["status"], "current")
            self.assertEqual(result["client_timeout"]["status"], "schema-unverified")

    def test_reports_cli_and_client_timeouts_separately_for_opencode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "opencode.jsonc"
            config.write_text(
                '{"mcp":{"serena":{"command":["serena","start-mcp-server","--tool-timeout","10"],"timeout":10000}}}\n',
                encoding="utf-8",
            )
            result = serena_safety.inspect_client_config(
                config,
                classification="active",
                client="opencode",
                expected_client_timeouts={"timeout": "milliseconds"},
            )
            self.assertEqual(result["classification"], "active")
            self.assertEqual(result["cli_tool_timeout"], {
                "value": 10.0,
                "expected": 10.0,
                "unit": "seconds",
                "status": "current",
            })
            self.assertEqual(result["client_timeout"]["values"], {"timeout": 10000.0})
            self.assertEqual(result["client_timeout"]["status"], "current")

    def test_reports_windows_utf8_environment_for_local_serena(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "opencode.jsonc"
            config.write_text(
                '{"mcp":{"serena":{"command":["serena","start-mcp-server","--tool-timeout","10"],'
                '"timeout":10000,"environment":{"PYTHONIOENCODING":"utf-8","PYTHONUTF8":"1"}}}}\n',
                encoding="utf-8",
            )
            result = serena_safety.inspect_client_config(
                config,
                classification="active",
                client="opencode",
                expected_client_timeouts={"timeout": "milliseconds"},
            )
            expected = "current" if os.name == "nt" else "not-applicable"
            self.assertEqual(result["windows_utf8_environment"]["status"], expected)

    def test_reports_codex_startup_and_tool_call_timeouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.toml"
            config.write_text(
                '[mcp_servers.serena]\nargs = ["start-mcp-server", "--tool-timeout", "10"]\n'
                'startup_timeout_sec = 10.0\ntool_timeout_sec = 10.0\n\n'
                '[mcp_servers.other]\nstartup_timeout_sec = 60.0\n',
                encoding="utf-8",
            )
            result = serena_safety.inspect_client_config(
                config,
                classification="active",
                client="codex",
                expected_client_timeouts={"startup_timeout_sec": "seconds", "tool_timeout_sec": "seconds"},
            )
            self.assertEqual(
                result["client_timeout"]["values"],
                {"startup_timeout_sec": 10.0, "tool_timeout_sec": 10.0},
            )
            self.assertEqual(result["client_timeout"]["status"], "current")

    def test_classifies_inactive_and_generated_candidates_without_direct_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inactive = root / "inactive.json"
            generated = root / "generated.json"
            inactive.write_text('{"mcpServers":{"serena":{"command":"serena"}}}\n', encoding="utf-8")
            generated.write_text(
                '{"mcpServers":{"serena":{"args":["--tool-timeout","10"]}}}\n',
                encoding="utf-8",
            )
            inactive_result = serena_safety.inspect_client_config(
                inactive,
                classification="inactive",
                client="antigravity",
                expected_client_timeouts={"timeout": "milliseconds"},
            )
            generated_result = serena_safety.inspect_client_config(
                generated,
                generated=True,
                client="claude",
            )
            self.assertEqual(inactive_result["classification"], "inactive")
            self.assertIn("Do not edit this candidate", inactive_result["remediation"])
            self.assertEqual(generated_result["classification"], "generated")
            self.assertIn("never edit", generated_result["remediation"])

    def test_candidate_matrix_includes_supported_generated_clients(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            specs = serena_safety.candidate_client_specs(root / "project", root / "home")
            generated_clients = {
                spec["client"] for spec in specs if spec["classification"] == "generated"
            }
            self.assertEqual(generated_clients, {"anythingllm", "claude", "codex", "hermes", "opencode"})
            self.assertIn("inactive", {spec["classification"] for spec in specs})
            self.assertIn("unknown", {spec["classification"] for spec in specs})
            self.assertIn("global-ssot", {spec["classification"] for spec in specs})

    def test_global_ssot_serena_entry_requires_deprovisioning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "servers.yaml"
            config.write_text('serena:\n  command: ["serena"]\n', encoding="utf-8")

            result = serena_safety.inspect_client_config(
                config,
                classification="global-ssot",
                client="host-ssot",
            )

            self.assertEqual(result["classification"], "global-ssot")
            self.assertIn("Remove Serena from the global host SSOT", result["remediation"])

    def test_reports_unverified_client_timeout_schemas_without_guessing(self) -> None:
        fixtures = {
            "claude": '{"mcpServers":{"serena":{"args":["--tool-timeout","10"]}}}\n',
            "hermes": 'mcp_servers:\n  "serena":\n    args: ["--tool-timeout", "10"]\n',
            "anythingllm": '{"mcpServers":{"serena":{"args":["--tool-timeout","10"]}}}\n',
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for client, text in fixtures.items():
                with self.subTest(client=client):
                    config = root / f"{client}.config"
                    config.write_text(text, encoding="utf-8")
                    result = serena_safety.inspect_client_config(config, generated=True, client=client)
                    self.assertEqual(result["classification"], "generated")
                    self.assertEqual(result["cli_tool_timeout"]["status"], "current")
                    self.assertEqual(result["client_timeout"]["status"], "schema-unverified")

    def test_reports_mcpm_serena_registry_without_writing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            registry = home / ".config" / "mcpm" / "servers.json"
            registry.parent.mkdir(parents=True)
            registry.write_text('{"serena": {"command": "uv"}}\n', encoding="utf-8")

            result = serena_safety.inspect_mcpm_serena_registry(home)

            self.assertEqual(result["status"], "present")
            self.assertTrue(result["contains_serena"])
            self.assertIn("mcpm uninstall serena", result["remediation"])
            self.assertIn('"serena"', registry.read_text(encoding="utf-8"))

    def test_reports_absent_mcpm_serena_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = serena_safety.inspect_mcpm_serena_registry(Path(temp))
            self.assertEqual(result["status"], "not-present")
            self.assertFalse(result["contains_serena"])

    def test_client_matrix_reports_actionable_classifications_without_false_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cwd = root / "project"
            home = root / "home"
            (cwd / "src").mkdir(parents=True)
            (cwd / "src" / "index.ts").write_text("export {};\n", encoding="utf-8")
            (cwd / ".serena").mkdir()
            (cwd / ".serena" / "project.yml").write_text(
                "languages: [typescript]\n",
                encoding="utf-8",
            )
            (home / ".serena").mkdir(parents=True)
            (home / ".serena" / "serena_config.yml").write_text(
                "tool_timeout: 10.0\n",
                encoding="utf-8",
            )
            cwd.joinpath("AGENTS.md").write_text(serena_safety.PROJECT_PLAYBOOK, encoding="utf-8")
            home.joinpath("AGENTS.md").write_text(serena_safety.PLAYBOOK, encoding="utf-8")

            fixtures = {
                cwd / "opencode.jsonc": (
                    '{"mcp":{"serena":{"command":["serena","start-mcp-server",'
                    '"--tool-timeout","10"],"timeout":10000,'
                    '"environment":{"PYTHONIOENCODING":"utf-8","PYTHONUTF8":"1"}}}}\n'
                ),
                cwd / ".agents" / "mcp_config.json": (
                    '{"mcpServers":{"serena":{"command":"serena"}}}\n'
                ),
                home / ".codex" / "config.toml": (
                    '[mcp_servers.serena]\nargs = ["start-mcp-server", "--tool-timeout", "10"]\n'
                    'startup_timeout_sec = 10\ntool_timeout_sec = 10\nPYTHONIOENCODING = "utf-8"\nPYTHONUTF8 = "1"\n'
                ),
                home / ".claude.json": (
                    '{"mcpServers":{"serena":{"args":["--tool-timeout","10"],'
                    '"env":{"PYTHONIOENCODING":"utf-8","PYTHONUTF8":"1"}}}}\n'
                ),
                home / ".hermes" / "config.yaml": (
                    'mcp_servers:\n  "serena":\n    args: ["--tool-timeout", "10"]\n'
                    '    env:\n      PYTHONIOENCODING: utf-8\n      PYTHONUTF8: "1"\n'
                ),
                home / ".config" / "mcp" / "generated" / "anythingllm-mcp.json": (
                    '{"mcpServers":{"serena":{"args":["--tool-timeout","30"]}}}\n'
                ),
            }
            for path, text in fixtures.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            report = serena_safety.build_report(cwd, home, apply=False)
            candidates = {
                (candidate["client"], candidate["classification"]): candidate
                for candidate in report["mcp_candidates"]
            }

            expected_utf8 = "current" if os.name == "nt" else "not-applicable"
            expected_statuses = {
                ("opencode", "unknown"): ("current", "current", expected_utf8),
                ("codex", "unknown"): ("current", "current", expected_utf8),
                ("claude", "unknown"): ("current", "schema-unverified", expected_utf8),
                ("hermes", "unknown"): ("current", "schema-unverified", expected_utf8),
            }
            for key, (cli_status, client_status, utf8_status) in expected_statuses.items():
                with self.subTest(client=key[0]):
                    self.assertEqual(candidates[key]["cli_tool_timeout"]["status"], cli_status)
                    self.assertEqual(candidates[key]["client_timeout"]["status"], client_status)
                    self.assertEqual(candidates[key]["windows_utf8_environment"]["status"], utf8_status)
                    self.assertIn("confirm the effective client source", candidates[key]["remediation"])

            antigravity = candidates[("antigravity", "inactive")]
            self.assertEqual(antigravity["cli_tool_timeout"]["status"], "missing")
            self.assertEqual(antigravity["client_timeout"]["status"], "update-needed")
            self.assertIn("Do not edit this candidate", antigravity["remediation"])

            anythingllm = candidates[("anythingllm", "generated")]
            self.assertEqual(anythingllm["cli_tool_timeout"]["status"], "update-needed")
            self.assertEqual(anythingllm["client_timeout"]["status"], "schema-unverified")
            self.assertIn("generating SSOT", anythingllm["remediation"])
            self.assertFalse(serena_safety.report_has_apply_failure(report))
            self.assertIn("leave inactive or unconfirmed candidates unchanged", report["next_action"])

    def test_timeout_precedence_reports_each_actionable_layer_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cwd = root / "project"
            home = root / "home"
            (cwd / "src").mkdir(parents=True)
            (cwd / "src" / "index.ts").write_text("export {};\n", encoding="utf-8")
            (cwd / ".serena").mkdir()
            (cwd / ".serena" / "project.yml").write_text(
                "languages: [typescript]\ntool_timeout: 10\n",
                encoding="utf-8",
            )
            (home / ".serena").mkdir(parents=True)
            (home / ".serena" / "serena_config.yml").write_text(
                "tool_timeout: 30\n",
                encoding="utf-8",
            )
            cwd.joinpath("AGENTS.md").write_text(serena_safety.PROJECT_PLAYBOOK, encoding="utf-8")
            home.joinpath("AGENTS.md").write_text(serena_safety.PLAYBOOK, encoding="utf-8")
            opencode = cwd / "opencode.jsonc"
            opencode.write_text(
                '{"mcp":{"serena":{"command":["serena","start-mcp-server",'
                '"--tool-timeout","10"],"timeout":10000,'
                '"environment":{"PYTHONIOENCODING":"utf-8","PYTHONUTF8":"1"}}}}\n',
                encoding="utf-8",
            )

            report = serena_safety.build_report(cwd, home, apply=False)
            active_opencode = next(
                candidate
                for candidate in report["mcp_candidates"]
                if candidate["path"] == str(opencode)
            )

            self.assertEqual(report["native_serena"]["global"]["status"], "update-needed")
            self.assertIn("tool_timeout to 10.0 seconds", report["native_serena"]["global"]["remediation"])
            self.assertEqual(report["native_serena"]["project"][0]["status"], "unsupported-key")
            self.assertIn("Remove tool_timeout", report["native_serena"]["project"][0]["remediation"])
            self.assertEqual(active_opencode["cli_tool_timeout"]["status"], "current")
            self.assertEqual(active_opencode["client_timeout"]["status"], "current")
            self.assertIn("confirm the effective client source", active_opencode["remediation"])
            self.assertEqual(
                report["native_serena"]["precedence"],
                "--tool-timeout CLI override > global serena_config.yml; project.yml has no tool_timeout field",
            )

    def test_read_only_client_findings_do_not_fail_managed_apply_status(self) -> None:
        report = {
            "native_serena": {"global": {"status": "current"}},
            "agents": [{"status": "managed-current"}],
            "mcp_candidates": [{"cli_tool_timeout": {"status": "missing"}}],
        }
        self.assertFalse(serena_safety.report_has_apply_failure(report))

    def test_selected_agents_apply_ignores_unselected_serena_failures(self) -> None:
        report = {
            "agents": [{"status": "written"}],
            "native_serena": {
                "global": {"status": "missing"},
                "project_initialization": {"status": "missing"},
                "languages": {"status": "missing"},
            },
        }
        self.assertFalse(
            serena_safety.report_has_selected_apply_failure(
                report,
                apply_agents=True,
                apply_serena=False,
                apply_languages=False,
            )
        )
        report["native_serena"]["global"]["status"] = "parse-error"
        self.assertFalse(
            serena_safety.report_has_selected_status(
                report,
                apply_agents=True,
                apply_serena=False,
                apply_languages=False,
                statuses={"parse-error"},
            )
        )

    def test_reports_missing_project_initialization_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = serena_safety.ensure_project_initialized(root, apply=False)
            self.assertEqual(result["status"], "missing")
            self.assertFalse(result["changed"])
            self.assertFalse((root / ".serena" / "project.yml").exists())

    def test_language_apply_does_not_initialize_serena(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            result = serena_safety.set_project_languages(root, apply=True)
            self.assertEqual(result["status"], "missing")
            self.assertFalse(result["changed"])
            self.assertFalse((root / ".serena" / "project.yml").exists())

    def test_agents_selection_updates_global_and_project_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cwd = root / "project"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()
            report = serena_safety.build_report(
                cwd,
                home,
                apply_agents=True,
                apply_serena=False,
                apply_languages=False,
            )
            self.assertEqual(report["requested_actions"], {"agents": True, "serena": False, "languages": False})
            self.assertIn(serena_safety.START, (home / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn(serena_safety.PROJECT_START, (cwd / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertFalse((cwd / ".serena").exists())

    def test_detects_only_project_source_languages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "index.ts").write_text("export {};\n", encoding="utf-8")
            (root / ".agents" / "skills").mkdir(parents=True)
            (root / ".agents" / "skills" / "helper.py").write_text("pass\n", encoding="utf-8")
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "main.py").write_text("pass\n", encoding="utf-8")
            self.assertEqual(serena_safety.detect_project_languages(root), {"typescript": 1})

    def test_detects_multiple_real_source_languages_by_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("pass\n", encoding="utf-8")
            (root / "src" / "one.ts").write_text("export {};\n", encoding="utf-8")
            (root / "src" / "two.ts").write_text("export {};\n", encoding="utf-8")
            self.assertEqual(serena_safety.detect_project_languages(root), {"typescript": 2, "python": 1})

    def test_omits_low_signal_helper_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            for index in range(20):
                (root / "src" / f"module-{index}.ts").write_text("export {};\n", encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts" / "helper.py").write_text("pass\n", encoding="utf-8")
            self.assertEqual(serena_safety.detect_project_languages(root), {"typescript": 20})

    def test_reports_meaningful_and_low_signal_language_candidates(self) -> None:
        candidates = serena_safety.classify_project_languages({"python": 1, "typescript": 20})
        self.assertEqual(
            [(candidate["language"], candidate["classification"]) for candidate in candidates],
            [("typescript", "meaningful"), ("python", "low-signal")],
        )

    def test_language_selection_is_deterministic_for_unsorted_counts(self) -> None:
        self.assertEqual(
            serena_safety.select_project_languages({"python": 5, "typescript": 5, "bash": 1}),
            {"python": 5, "typescript": 5},
        )

    def test_low_signal_helper_does_not_create_remediation_when_languages_are_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            for index in range(20):
                (root / "src" / f"module-{index}.ts").write_text("export {};\n", encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts" / "helper.py").write_text("pass\n", encoding="utf-8")
            (root / ".serena").mkdir()
            (root / ".serena" / "project.yml").write_text(
                "languages: [typescript]\n",
                encoding="utf-8",
            )

            result = serena_safety.set_project_languages(root, apply=False)

            self.assertEqual(result["status"], "current")
            self.assertEqual(result["configured"], ["typescript"])
            self.assertEqual(result["ignored_low_signal"], {"python": 1})
            self.assertEqual(
                [(candidate["language"], candidate["classification"]) for candidate in result["language_candidates"]],
                [("typescript", "meaningful"), ("python", "low-signal")],
            )
            self.assertIsNone(result["remediation"])

    def test_replaces_extra_project_languages(self) -> None:
        text = "languages:\n- typescript\n- python\n\nencoding: utf-8\n"
        updated = serena_safety.replace_configured_languages(text, ["typescript"])
        self.assertEqual(serena_safety.parse_configured_languages(updated), ["typescript"])
        self.assertNotIn("- python", updated)
        self.assertIn("encoding: utf-8", updated)

    def test_updates_inline_project_languages_idempotently(self) -> None:
        text = "languages: [python, typescript]\nencoding: utf-8\n"
        updated = serena_safety.replace_configured_languages(text, ["typescript"])
        self.assertEqual(serena_safety.parse_configured_languages(updated), ["typescript"])
        self.assertEqual(serena_safety.replace_configured_languages(updated, ["typescript"]), updated)

    def test_writes_valid_empty_language_list(self) -> None:
        text = "languages:\n- python\nencoding: utf-8\n"
        updated = serena_safety.replace_configured_languages(text, [])
        self.assertEqual(serena_safety.parse_configured_languages(updated), [])
        self.assertIn("languages: []", updated)

    def test_clears_languages_from_global_serena_metadata_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            config = home / ".serena" / ".serena" / "project.yml"
            config.parent.mkdir(parents=True)
            config.write_text("languages: [dart]\n", encoding="utf-8")

            result = serena_safety.clear_global_metadata_languages(home, apply=True)

            self.assertEqual(result["status"], "written")
            self.assertEqual(serena_safety.parse_configured_languages(config.read_text(encoding="utf-8")), [])

    def test_clears_effective_global_metadata_local_language_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            config = home / ".serena" / ".serena" / "project.yml"
            local = home / ".serena" / ".serena" / "project.local.yml"
            config.parent.mkdir(parents=True)
            config.write_text("languages: []\n", encoding="utf-8")
            local.write_text("languages: [dart]\n", encoding="utf-8")

            result = serena_safety.clear_global_metadata_languages(home, apply=True)

            self.assertEqual(result["source"], "project.local.yml")
            self.assertEqual(serena_safety.parse_configured_languages(local.read_text(encoding="utf-8")), [])
            self.assertEqual(serena_safety.parse_configured_languages(config.read_text(encoding="utf-8")), [])

    def test_preserves_absent_global_serena_metadata_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = serena_safety.clear_global_metadata_languages(Path(temp), apply=True)
            self.assertEqual(result["status"], "not-present")

    def test_updates_effective_project_local_language_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "index.ts").write_text("export {};\n", encoding="utf-8")
            serena_dir = root / ".serena"
            serena_dir.mkdir()
            base = serena_dir / "project.yml"
            local = serena_dir / "project.local.yml"
            base.write_text("languages:\n- python\n", encoding="utf-8")
            local.write_text("languages:\n- python\n", encoding="utf-8")
            result = serena_safety.set_project_languages(root, apply=True)
            self.assertEqual(result["source"], "project.local.yml")
            self.assertEqual(serena_safety.parse_configured_languages(local.read_text(encoding="utf-8")), ["typescript"])
            self.assertEqual(serena_safety.parse_configured_languages(base.read_text(encoding="utf-8")), ["python"])

    def test_preserves_relevant_language_server_variant(self) -> None:
        configured = ["typescript_vts", "python_jedi"]
        self.assertEqual(
            serena_safety.preserve_language_variants(["typescript"], configured),
            ["typescript_vts"],
        )

    def test_parses_commented_language_list_and_preserves_comment(self) -> None:
        text = "languages:\n# Keep this project-specific note.\n- python\nencoding: utf-8\n"
        self.assertEqual(serena_safety.parse_configured_languages(text), ["python"])
        updated = serena_safety.replace_configured_languages(text, ["typescript"])
        self.assertIn("# Keep this project-specific note.", updated)
        self.assertEqual(serena_safety.parse_configured_languages(updated), ["typescript"])

    def test_parses_quoted_numeric_timeout(self) -> None:
        self.assertEqual(serena_safety.yaml_top_level_number('tool_timeout: "10"\n', "tool_timeout"), 10.0)

    def test_rejects_null_languages(self) -> None:
        with self.assertRaisesRegex(ValueError, "not null"):
            serena_safety.parse_configured_languages("languages: null\n")

    def test_removes_unsupported_project_timeout_on_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".serena" / "project.yml"
            path.parent.mkdir()
            path.write_text("languages: []\ntool_timeout: 10\n", encoding="utf-8")
            result = serena_safety.inspect_project_config(path, apply=True)
            self.assertEqual(result["status"], "removed-unsupported-key")
            self.assertNotIn("tool_timeout", path.read_text(encoding="utf-8"))

    def test_refuses_home_as_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            with self.assertRaisesRegex(ValueError, "Refusing broad project audit"):
                serena_safety.validate_project_root(home, home)

    def test_refuses_write_outside_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            outside = Path(temp) / "outside.txt"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "outside"):
                serena_safety.safe_write_text(outside, "unsafe", root)

    def test_preserves_crlf_when_updating_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "AGENTS.md"
            path.write_bytes(b"Header\r\n")
            serena_safety.update_agents(path, apply=True)
            content = path.read_bytes()
            self.assertIn(b"\r\n", content)
            self.assertNotIn(b"\n", content.replace(b"\r\n", b""))

    def test_wraps_invalid_yaml_as_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid YAML"):
            serena_safety.load_yaml_mapping("languages: [typescript\n")

    def test_restores_cross_file_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = root / "existing.yml"
            created = root / "created.yml"
            existing.write_bytes(b"original\r\n")
            snapshots = serena_safety.capture_snapshots([existing, created])
            existing.write_bytes(b"changed\n")
            created.write_bytes(b"new\n")
            serena_safety.restore_snapshots(snapshots)
            self.assertEqual(existing.read_bytes(), b"original\r\n")
            self.assertFalse(created.exists())

    def test_manages_global_and_project_agents_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cwd = root / "project"
            home = root / "home"
            paths = serena_safety.managed_paths(cwd, home)

            self.assertIn(home / "AGENTS.md", paths)
            self.assertIn(cwd / "AGENTS.md", paths)

    def test_audit_reports_remediation_without_mutating_configs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cwd = root / "project"
            home = root / "home"
            (cwd / "src").mkdir(parents=True)
            home.mkdir()
            for index in range(20):
                (cwd / "src" / f"module-{index}.ts").write_text("export {};\n", encoding="utf-8")
            (cwd / "scripts").mkdir()
            (cwd / "scripts" / "helper.py").write_text("pass\n", encoding="utf-8")
            (cwd / ".serena").mkdir()
            project_config = cwd / ".serena" / "project.yml"
            project_config.write_text("languages: [typescript, python]\ntool_timeout: 30\n", encoding="utf-8")
            (home / ".serena").mkdir()
            global_config = home / ".serena" / "serena_config.yml"
            global_config.write_text("tool_timeout: 30\n", encoding="utf-8")
            (cwd / ".agents").mkdir()
            client_config = cwd / ".agents" / "mcp_config.json"
            client_config.write_text(
                '{"mcpServers":{"serena":{"command":"serena"}}}\n',
                encoding="utf-8",
            )
            before = {
                path: path.read_bytes() for path in (project_config, global_config, client_config)
            }

            report = serena_safety.build_report(cwd, home, apply=False)

            self.assertEqual(report["mode"], "audit")
            self.assertEqual(report["native_serena"]["global"]["status"], "update-needed")
            self.assertEqual(report["timeout_policy"]["global_serena"]["unit"], "seconds")
            self.assertEqual(len(report["timeout_policy"]["cli_overrides"]), 1)
            self.assertEqual(len(report["timeout_policy"]["client_boundaries"]), 1)
            self.assertEqual(report["native_serena"]["languages"]["ignored_low_signal"], {"python": 1})
            self.assertTrue(report["native_serena"]["languages"]["remediation"])
            self.assertEqual(report["mcp_candidates"][0]["classification"], "inactive")
            self.assertTrue(report["mcp_candidates"][0]["remediation"])
            self.assertEqual(
                before,
                {path: path.read_bytes() for path in (project_config, global_config, client_config)},
            )


if __name__ == "__main__":
    unittest.main()
