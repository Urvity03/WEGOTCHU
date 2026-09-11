import json
import re
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_critical_directories_exist():
    expected_dirs = [
        "docs/architecture",
        "docs/research",
        "docs/safety",
        "docs/project",
        "ai/anomaly_detection",
        "ai/personalization",
        "ai/temporal_model",
        "ai/multimodal_fusion",
        "ai/risk_engine",
        "ai/genai",
        "perception/audio",
        "perception/vision",
        "perception/edge",
        "data/raw",
        "data/processed",
        "data/features",
        "backend",
        "mobile",
        "experiments",
        "tests",
        "scripts",
        "configs",
        ".github/workflows",
        ".github/ISSUE_TEMPLATE",
    ]
    for rel_dir in expected_dirs:
        dir_path = REPO_ROOT / rel_dir
        assert dir_path.is_dir(), f"Expected directory missing: {rel_dir}"


def test_critical_files_exist():
    expected_files = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".gitignore",
        ".env.example",
        "requirements.txt",
        "docs/architecture/system-architecture.md",
        "docs/architecture/ai-architecture.md",
        "docs/architecture/data-flow.md",
        "docs/architecture/component-interactions.md",
        "docs/research/research-question.md",
        "docs/research/datasets.md",
        "docs/research/literature-review.md",
        "docs/research/related-work.md",
        "docs/safety/ai-safety-policy.md",
        "docs/safety/threat-model.md",
        "docs/safety/privacy.md",
        "docs/safety/data-retention.md",
        "docs/project/requirements.md",
        "docs/project/roadmap.md",
        "docs/project/milestones.md",
        "docs/project/team-responsibilities.md",
        "docs/project/meeting-notes.md",
        "docs/project/issue-backlog.md",
        "docs/project/project-board.md",
        ".github/workflows/ci.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/ISSUE_TEMPLATE/research_experiment.md",
    ]
    for rel_file in expected_files:
        file_path = REPO_ROOT / rel_file
        assert file_path.is_file(), f"Expected file missing: {rel_file}"
        assert (
            file_path.stat().st_size > 50
        ), f"File appears too small or empty: {rel_file}"


def test_gitignore_covers_security_and_data():
    gitignore_path = REPO_ROOT / ".gitignore"
    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
    assert "data/raw/*" in content
    assert "*.pt" in content
    assert "*.onnx" in content
    assert "__pycache__/" in content


def test_data_flow_json_blocks():
    data_flow_path = REPO_ROOT / "docs/architecture/data-flow.md"
    content = data_flow_path.read_text(encoding="utf-8")
    # Extract json code blocks
    json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    assert (
        len(json_blocks) >= 4
    ), "Expected at least 4 JSON contract examples in data-flow.md"
    for block in json_blocks:
        parsed = json.loads(block)
        assert isinstance(parsed, dict)
