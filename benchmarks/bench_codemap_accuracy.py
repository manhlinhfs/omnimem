"""Codemap parser accuracy benchmark.

For each supported language we ship a small synthetic source file plus the
expected list of top-level symbols (the ground truth). The benchmark runs the
parser, compares the captured symbols against the ground truth, and reports
precision / recall / F1 per language.

This is a regression guard, not an exhaustive accuracy claim. Real-world
fidelity will vary; the regex parsers favor the common case over total
coverage.

Run from the repo root:

    python -m benchmarks.bench_codemap_accuracy
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.common import write_result  # noqa: E402

PYTHON_SOURCE = '''"""Module docstring."""

import os
from pathlib import Path

CONST = 1


def alpha(x, y):
    """alpha doc."""
    return x + y


async def beta():
    pass


class Gamma(Base):
    """gamma."""

    def __init__(self, value):
        self.value = value

    async def emit(self):
        pass
'''

PYTHON_EXPECTED = {"alpha", "beta", "Gamma", "Gamma.__init__", "Gamma.emit"}


JAVASCRIPT_SOURCE = """import React from 'react';
import './styles.css';

export class Widget extends React.Component {
  render() {
    return null;
  }
}

export default function helper(name) {
  return name;
}

export const arrow = async (id) => id;
"""

JAVASCRIPT_EXPECTED = {"Widget", "helper", "arrow"}


TYPESCRIPT_SOURCE = """interface User {
  id: string;
  name: string;
}

type Callback = (input: string) => void;

enum Color {
  Red,
  Green,
}

export function login(user: User): boolean {
  return true;
}

export class Service {}
"""

TYPESCRIPT_EXPECTED = {"User", "Callback", "Color", "login", "Service"}


GO_SOURCE = """package server

import (
    "fmt"
    "net/http"
)

type Handler struct {
    name string
}

type Logger interface {
    Log(line string)
}

func New(name string) *Handler {
    return &Handler{name: name}
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    fmt.Println(h.name)
}
"""

GO_EXPECTED = {"Handler", "Logger", "New", "Handler.ServeHTTP"}


RUST_SOURCE = """use std::collections::HashMap;

pub struct Config {
    name: String,
}

pub enum Status {
    Ready,
    Failed,
}

trait Renderer {
    fn render(&self) -> String;
}

impl Config {
    pub fn new(name: &str) -> Config {
        Config { name: name.to_string() }
    }
}

pub fn run() -> Status {
    Status::Ready
}
"""

RUST_EXPECTED = {"Config", "Status", "Renderer", "Config", "run", "new", "render"}


CASES = [
    ("python", PYTHON_SOURCE, PYTHON_EXPECTED, "demo.py"),
    ("javascript", JAVASCRIPT_SOURCE, JAVASCRIPT_EXPECTED, "demo.js"),
    ("typescript", TYPESCRIPT_SOURCE, TYPESCRIPT_EXPECTED, "demo.ts"),
    ("go", GO_SOURCE, GO_EXPECTED, "demo.go"),
    ("rust", RUST_SOURCE, RUST_EXPECTED, "demo.rs"),
]


def _captured_symbols(model):
    names = set()
    for cls in model.get("classes") or []:
        names.add(cls["name"])
        for method in cls.get("methods") or []:
            names.add(f"{cls['name']}.{method['name']}")
    for func in model.get("functions") or []:
        names.add(func["name"])
    return names


def _score(captured, expected):
    captured_set = set(captured)
    expected_set = set(expected)
    true_positive = len(captured_set & expected_set)
    false_positive = len(captured_set - expected_set)
    false_negative = len(expected_set - captured_set)
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "expected": sorted(expected_set),
        "captured": sorted(captured_set),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def run():
    from omni_codemap import LANGUAGE_PARSERS

    per_language = {}
    weighted_precision = []
    weighted_recall = []
    for language, source, expected, path in CASES:
        parser = LANGUAGE_PARSERS[language]
        if language == "typescript":
            model = parser(source, path=path)
        else:
            model = parser(source, path=path)
        captured = _captured_symbols(model)
        score = _score(captured, expected)
        per_language[language] = score
        weighted_precision.append(score["precision"])
        weighted_recall.append(score["recall"])

    aggregate = {
        "macro_precision": sum(weighted_precision) / len(weighted_precision),
        "macro_recall": sum(weighted_recall) / len(weighted_recall),
    }
    aggregate["macro_f1"] = (
        2 * aggregate["macro_precision"] * aggregate["macro_recall"]
        / (aggregate["macro_precision"] + aggregate["macro_recall"])
        if (aggregate["macro_precision"] + aggregate["macro_recall"])
        else 0.0
    )

    return {
        "tool": "omnimem-bench-codemap-accuracy",
        "languages": per_language,
        "aggregate": aggregate,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="OmniMem codemap parser accuracy")
    parser.add_argument("--save", default="codemap_accuracy")
    args = parser.parse_args(argv)
    report = run()
    target = write_result(args.save, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {target}")


if __name__ == "__main__":
    main()
