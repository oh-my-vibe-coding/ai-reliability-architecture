"""
04-eval-skeleton.py
---
最小 Eval pipeline：L1 assertion + L2 judge。
Pydantic 做 schema，pytest 做 gate。

演示：
- 三层 Eval 里的 L1 和 L2
- Judge 对齐度追踪的地方（人工标注位）
- 如何把 eval 跑成 CI/pytest 门禁

对应章节：深入 06 · Eval Pipeline 设计
"""

import json
import statistics
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, ValidationError
from anthropic import Anthropic

claude = Anthropic()


# ---- 1. 定义我们产品的输出 schema ----


class RunbookStep(BaseModel):
    """一条 runbook 建议"""

    step: int
    action: str
    safety: str  # low / medium / high
    reversible: bool


class RunbookResponse(BaseModel):
    root_cause_guess: str
    steps: list[RunbookStep]
    references: list[str]  # 必须有出处


# ---- 2. 我们产品的"被测函数" ----


SYSTEM_PROMPT = """你是 SRE 助手。输出必须符合 JSON schema。
必须包含：root_cause_guess（根因猜测）、steps（步骤列表）、references（每个建议的出处）。
每个 step 必须有 step 编号、action、safety（low/medium/high）、reversible（布尔）。

只输出 JSON，不要其他文字。"""


def generate_runbook(incident_description: str) -> Optional[dict]:
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": incident_description}],
    )
    text = response.content[0].text.strip()
    # 清理常见的 markdown 包裹
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---- 3. L1 · Assertion（硬规则）----


def l1_check(raw: dict | None) -> dict:
    """返回每条规则的通过情况"""
    if raw is None:
        return {"parseable": False}

    result = {"parseable": True}

    # 是否符合 schema
    try:
        parsed = RunbookResponse(**raw)
        result["schema_valid"] = True
    except ValidationError as e:
        result["schema_valid"] = False
        result["schema_errors"] = str(e)
        return result

    # 业务硬规则
    result["has_references"] = len(parsed.references) > 0
    result["steps_numbered_correctly"] = all(
        s.step == i + 1 for i, s in enumerate(parsed.steps)
    )
    result["no_kill_minus_9"] = not any("kill -9" in s.action.lower() for s in parsed.steps)
    result["reversible_safety_align"] = all(
        not (s.safety == "high" and s.reversible) for s in parsed.steps
    )

    return result


# ---- 4. L2 · Judge 模型评分 ----


JUDGE_PROMPT = """你是一个严格的 SRE 评委。

根据以下原始 incident 描述和 SRE 助手给出的建议，
打 1-10 分（10 最好）评三项：

1. relevance：建议和问题相关度
2. safety：建议的安全性
3. completeness：覆盖完整度

输出 JSON：{"relevance": int, "safety": int, "completeness": int, "reasoning": str}

只输出 JSON。

Incident: {incident}

Response: {response}
"""


@dataclass
class JudgeScore:
    relevance: int
    safety: int
    completeness: int
    reasoning: str


def l2_judge(incident: str, response: dict) -> Optional[JudgeScore]:
    prompt = JUDGE_PROMPT.format(incident=incident, response=json.dumps(response))
    result = claude.messages.create(
        model="claude-haiku-4-5",  # 用更便宜的做 judge
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = result.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "", 1)
    try:
        data = json.loads(text)
        return JudgeScore(**data)
    except (json.JSONDecodeError, TypeError):
        return None


# ---- 5. Judge 对齐度追踪（手动标注样本） ----


def measure_alignment(samples: list[dict]) -> dict:
    """
    samples: [{"incident": ..., "response": ..., "human_score": {...}, "judge_score": {...}}]
    返回每维度的 human vs judge 相关性
    """
    results = {}
    for dim in ["relevance", "safety", "completeness"]:
        human = [s["human_score"][dim] for s in samples]
        judge = [s["judge_score"][dim] for s in samples]

        # 简单 agreement rate（差 <=1 算对齐）
        agreement = sum(1 for h, j in zip(human, judge) if abs(h - j) <= 1) / len(samples)
        results[dim] = {
            "agreement_rate": agreement,
            "human_mean": statistics.mean(human),
            "judge_mean": statistics.mean(judge),
            "judge_bias": statistics.mean(judge) - statistics.mean(human),
        }
    return results


# ---- 6. Eval Gate（可作为 pytest / CI 门禁）----


@dataclass
class EvalReport:
    total: int
    l1_pass_rate: float
    l2_avg_scores: dict
    failures: list[dict]


def run_eval_suite(incidents: list[str]) -> EvalReport:
    failures = []
    l1_pass_count = 0
    l2_scores = {"relevance": [], "safety": [], "completeness": []}

    for incident in incidents:
        raw = generate_runbook(incident)
        l1 = l1_check(raw)
        l1_ok = all(v for k, v in l1.items() if isinstance(v, bool))
        if l1_ok:
            l1_pass_count += 1
        else:
            failures.append({"incident": incident, "l1": l1, "raw": raw})
            continue

        l2 = l2_judge(incident, raw)
        if l2:
            l2_scores["relevance"].append(l2.relevance)
            l2_scores["safety"].append(l2.safety)
            l2_scores["completeness"].append(l2.completeness)

    return EvalReport(
        total=len(incidents),
        l1_pass_rate=l1_pass_count / len(incidents),
        l2_avg_scores={k: statistics.mean(v) for k, v in l2_scores.items() if v},
        failures=failures,
    )


# ---- 7. CI 门禁示例 ----


def ci_gate(report: EvalReport):
    """pytest / CI 可以调用这个，不过则 exit 1"""
    assert report.l1_pass_rate > 0.95, f"L1 pass rate too low: {report.l1_pass_rate:.1%}"
    assert report.l2_avg_scores.get("safety", 0) >= 8, "Safety score too low"
    assert report.l2_avg_scores.get("relevance", 0) >= 7, "Relevance too low"
    print("✓ Eval gate passed")


# ---- 8. 运行 ----

if __name__ == "__main__":
    test_incidents = [
        "生产 mysql 主库 CPU 100%，慢查询激增",
        "k8s 一个 node 上所有 pod 都在 CrashLoopBackOff",
        "用户报告登录 API 延迟 p99 从 200ms 飙到 3s",
    ]

    report = run_eval_suite(test_incidents)
    print(f"\n=== Eval Report ===")
    print(f"Total: {report.total}")
    print(f"L1 pass rate: {report.l1_pass_rate:.1%}")
    print(f"L2 scores: {report.l2_avg_scores}")
    if report.failures:
        print(f"\n{len(report.failures)} failures detected")

    # ci_gate(report)  # 生产 CI 里启用这行作为 gate

    # ---- 下一步 ----
    # 1. 加 L3（线上 A/B，不只是 offline）
    # 2. 人工标注流（UI 让工程师给 judge 打分）
    # 3. 持续漂移监控（judge 对齐度跌就报警）
    # 4. Gold Set 版本化
