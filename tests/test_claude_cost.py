"""Offline tests for claude_cost.py with small synthetic transcripts."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claude_cost  # noqa: E402

PRICES = claude_cost.load_prices()
MILLION = {"input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000, "cache_write_5m_tokens": 1_000_000,
           "cache_write_1h_tokens": 1_000_000, "output_tokens": 1_000_000}


def assistant_line(msg_id, model, usage, effort="high", timestamp="2026-10-07T10:00:00Z"):
    return json.dumps({"type": "assistant", "effort": effort, "timestamp": timestamp,
                       "message": {"id": msg_id, "model": model, "usage": usage}}) + "\n"


def test_one_million_of_each_token_type_on_opus_5_5():
    # input 4 + read 0.2 + 5m write 5 + 1h write 8 + output 20
    assert claude_cost.price(MILLION, "claude-opus-5-5", "list", PRICES) == pytest.approx(37.2)
    assert claude_cost.price(MILLION, "claude-opus-5-5", "gateway", PRICES) == pytest.approx(14.88)


def test_gateway_is_forty_percent_of_list_for_every_model():
    for model in PRICES["models"]:
        assert claude_cost.price(MILLION, model, "gateway", PRICES) == pytest.approx(0.4 * claude_cost.price(MILLION, model, "list", PRICES))


def test_fable_5_1_at_max_effort_bills_three_times_at_the_gateway():
    usage = dict(MILLION)
    base = claude_cost.price(usage, "claude-fable-5-1", "gateway", PRICES, "high")
    assert claude_cost.price(usage, "claude-fable-5-1", "gateway", PRICES, "max") == pytest.approx(3 * base)
    assert claude_cost.price(usage, "claude-opus-5-5", "gateway", PRICES, "max") == pytest.approx(14.88)


def test_unknown_model_has_no_price():
    assert claude_cost.price(MILLION, "<synthetic>", "list", PRICES) is None


def test_cache_creation_is_split_by_ttl():
    usage = claude_cost.normalize({"input_tokens": 5, "cache_creation_input_tokens": 300,
                                   "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 200},
                                   "cache_read_input_tokens": 50, "output_tokens": 7})
    assert usage == {"input_tokens": 5, "cache_read_input_tokens": 50, "cache_write_5m_tokens": 100,
                     "cache_write_1h_tokens": 200, "output_tokens": 7}


def test_writes_without_breakdown_count_as_five_minute():
    assert claude_cost.normalize({"cache_creation_input_tokens": 900})["cache_write_5m_tokens"] == 900


def test_transcripts_count_each_message_once_and_include_subagents(tmp_path):
    usage = {"input_tokens": 10, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 0, "output_tokens": 50}
    project = tmp_path / "-home-dev-app"
    (project / "session-1" / "subagents").mkdir(parents=True)
    with open(project / "session-1.jsonl", "w") as handle:
        handle.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
        handle.write(assistant_line("msg_a", "claude-opus-5-5", usage))
        handle.write(assistant_line("msg_a", "claude-opus-5-5", usage))  # same response, second content block
        handle.write(assistant_line("msg_old", "claude-opus-5-5", usage, timestamp="2026-09-01T00:00:00Z"))
    with open(project / "session-1" / "subagents" / "agent-1.jsonl", "w") as handle:
        handle.write(assistant_line("msg_b", "claude-sonnet-5", usage, effort="low"))
    totals = claude_cost.read_transcripts(str(tmp_path), since="2026-10-01")
    assert totals[("claude-opus-5-5", "high")]["cache_read_input_tokens"] == 1000
    assert totals[("claude-sonnet-5", "low")]["output_tokens"] == 50
    assert len(totals) == 2


def test_estimate_command_prints_a_row_per_model(tmp_path, capsys):
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"usage": {"input_tokens": 1_000_000, "output_tokens": 0}}))
    assert claude_cost.main(["estimate", str(path), "--models", "claude-opus-5,claude-sonnet-5"]) == 0
    out = capsys.readouterr().out
    assert "| usage | `claude-opus-5` | $5.00 | $2.00 | 0% |" in out
    assert "| usage | `claude-sonnet-5` | $2.00 | $0.8000 | 0% |" in out


def test_transcripts_command_reports_totals_and_what_if(tmp_path, capsys):
    usage = {"input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 1_000_000}
    (tmp_path / "s.jsonl").write_text(assistant_line("m1", "claude-opus-5", usage))
    assert claude_cost.main(["transcripts", "--root", str(tmp_path), "--what-if", "claude-sonnet-5"]) == 0
    out = capsys.readouterr().out
    assert "Total: $25.00 at Anthropic list price, $10.00 at gateway rates" in out
    assert "Same tokens on claude-sonnet-5: $10.00 list, $4.00 gateway." in out


def test_example_files_parse():
    root = os.path.join(os.path.dirname(__file__), "..", "examples")
    for name in ("scenarios.json", "response.json"):
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            json.load(handle)
