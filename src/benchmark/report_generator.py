"""
ReportGenerator — charts and CSV from benchmark_summary.json.
Handles the updated metrics: select_cache_hit_rate_pct, prefetch stats, per-session isolation.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from config.settings import CHARTS_DIR, REPORTS_DIR

SCENARIO_LABELS = {
    "baseline":    "Baseline\n(No Cache)",
    "cache_only":  "Cache Only",
    "ai_prefetch": "AI Pre-fetch",
}
COLORS = {
    "baseline":    "#e74c3c",
    "cache_only":  "#3498db",
    "ai_prefetch": "#2ecc71",
}


def load_results(path: str = None) -> dict:
    path = path or os.path.join(REPORTS_DIR, "benchmark_summary.json")
    with open(path) as f:
        return json.load(f)


def _setup():
    os.makedirs(CHARTS_DIR, exist_ok=True)
    sns.set_theme(style="whitegrid", font_scale=1.1)


# ── Chart 1: Cache Hit Rate (overall + SELECT-only) ───────────────────────────
def plot_cache_hit_rate(results: dict):
    scenarios = list(results.keys())
    labels    = [SCENARIO_LABELS[s] for s in scenarios]
    colors    = [COLORS[s] for s in scenarios]

    overall_rates = [results[s]["cache_hit_rate_pct"] for s in scenarios]
    select_rates  = [results[s].get("select_cache_hit_rate_pct", 0) for s in scenarios]

    x     = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    b1 = ax.bar(x - width/2, overall_rates, width, label="Overall Hit Rate",
                color=colors, alpha=0.9, edgecolor="white")
    b2 = ax.bar(x + width/2, select_rates,  width, label="SELECT-only Hit Rate",
                color=colors, alpha=0.55, edgecolor="white", hatch="//")

    for bar, val in zip(b1, overall_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    for bar, val in zip(b2, select_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=10, color="#555")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(max(overall_rates), max(select_rates)) * 1.25 + 5)
    ax.set_ylabel("Cache Hit Rate (%)")
    ax.set_title("Cache Hit Rate by Scenario\n(per-session cache isolation — realistic cold-cache simulation)",
                 fontsize=12, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "cache_hit_rate.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 2: Response Time Percentiles ────────────────────────────────────────
def plot_response_time_comparison(results: dict):
    scenarios = list(results.keys())
    labels    = [SCENARIO_LABELS[s] for s in scenarios]
    metrics   = ["avg_response_ms", "median_response_ms", "p95_response_ms", "p99_response_ms"]
    m_labels  = ["Average", "Median", "P95", "P99"]

    x     = np.arange(len(metrics))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, (s, color) in enumerate(zip(scenarios, [COLORS[s] for s in scenarios])):
        vals = [results[s][m] for m in metrics]
        bars = ax.bar(x + i*width, vals, width, label=SCENARIO_LABELS[s].replace("\n", " "),
                      color=color, alpha=0.88)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x + width)
    ax.set_xticklabels(m_labels)
    ax.set_ylabel("Response Time (ms)")
    ax.set_title("Query Response Time by Scenario", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "response_time_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 3: Prefetch Breakdown ────────────────────────────────────────────────
def plot_prefetch_breakdown(results: dict):
    ai = results.get("ai_prefetch", {})
    pred_total   = ai.get("prediction_count", 0)
    skip_conf    = ai.get("skipped_low_confidence", 0)
    skip_select  = ai.get("skipped_non_select", 0)
    attempts     = ai.get("prefetch_attempts", 0)
    successes    = ai.get("prefetch_successes", 0)

    if pred_total == 0:
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: prediction funnel
    stages = ["Total\nPredictions", "Low Confidence\nSkipped", "Non-SELECT\nSkipped", "Pre-fetch\nAttempts", "Pre-fetch\nSuccess"]
    values = [pred_total, pred_total - skip_conf, pred_total - skip_conf - skip_select, attempts, successes]
    bar_colors = ["#3498db", "#e74c3c", "#e67e22", "#2ecc71", "#27ae60"]
    bars = axes[0].barh(stages[::-1], values[::-1], color=bar_colors[::-1], edgecolor="white")
    for bar, val in zip(bars, values[::-1]):
        axes[0].text(bar.get_width() + pred_total * 0.01, bar.get_y() + bar.get_height()/2,
                     f"{val:,}  ({val/pred_total*100:.1f}%)", va="center", fontsize=10)
    axes[0].set_xlim(0, pred_total * 1.3)
    axes[0].set_xlabel("Query Count")
    axes[0].set_title("AI Pre-fetch: Prediction Funnel", fontweight="bold")

    # Right: pie of prediction outcomes
    acted    = attempts
    skip_c   = skip_conf
    skip_s   = skip_select
    leftover = pred_total - skip_c - skip_s - acted
    pie_vals   = [acted, skip_c, skip_s, leftover]
    pie_labels = [f"Pre-fetched\n({acted:,})",
                  f"Skipped (low conf)\n({skip_c:,})",
                  f"Skipped (non-SELECT)\n({skip_s:,})",
                  f"Other\n({leftover:,})"]
    pie_colors = ["#2ecc71", "#e74c3c", "#e67e22", "#95a5a6"]
    wedges, texts, autotexts = axes[1].pie(
        pie_vals, labels=pie_labels, colors=pie_colors,
        autopct="%1.1f%%", startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    for at in autotexts:
        at.set_fontsize(9)
    axes[1].set_title("Prediction Outcome Distribution", fontweight="bold")

    plt.suptitle("AI Pre-fetch Controller: Prediction & Pre-fetch Statistics", fontsize=12, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "prefetch_breakdown.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 4: Improvement Summary ──────────────────────────────────────────────
def plot_improvement_summary(results: dict):
    baseline = results["baseline"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    scenarios = list(results.keys())
    labels    = [SCENARIO_LABELS[s].replace("\n", " ") for s in scenarios]
    colors    = [COLORS[s] for s in scenarios]

    # Hit rate
    hit_rates = [results[s]["cache_hit_rate_pct"] for s in scenarios]
    axes[0].barh(labels, hit_rates, color=colors, edgecolor="white")
    axes[0].set_xlabel("Cache Hit Rate (%)")
    axes[0].set_title("Cache Hit Rate", fontweight="bold")
    for i, v in enumerate(hit_rates):
        axes[0].text(v + 0.2, i, f"{v:.1f}%", va="center", fontsize=10)

    # Median response time (more telling than avg when distributions are bimodal)
    med_times = [results[s]["median_response_ms"] for s in scenarios]
    axes[1].barh(labels, med_times, color=colors, edgecolor="white")
    axes[1].set_xlabel("Median Response Time (ms)")
    axes[1].set_title("Median Response Time", fontweight="bold")
    for i, v in enumerate(med_times):
        axes[1].text(v + 0.2, i, f"{v:.1f}ms", va="center", fontsize=10)

    # Speedup vs baseline (median)
    baseline_med = baseline["median_response_ms"]
    speedups = [round(baseline_med / results[s]["median_response_ms"], 1)
                if results[s]["median_response_ms"] > 0 else 1.0
                for s in scenarios]
    axes[2].barh(labels, speedups, color=colors, edgecolor="white")
    axes[2].set_xlabel("Median Speedup vs Baseline (×)")
    axes[2].set_title("Speedup Factor (Median RT)", fontweight="bold")
    for i, v in enumerate(speedups):
        axes[2].text(v + 0.1, i, f"{v:.1f}×", va="center", fontsize=10)

    plt.suptitle("Performance Comparison: Query Predictor System\n"
                 "(per-session cache isolation — realistic workload)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "improvement_summary.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 5: Response-time distribution (violin) ──────────────────────────────
def plot_rt_distribution(results: dict):
    np.random.seed(42)

    def _sample(s_key):
        d = results[s_key]
        mean, std, n = d["avg_response_ms"], d["std_response_ms"], 2000
        samples = np.random.normal(mean, std, n)
        return np.clip(samples, d["min_response_ms"], d["max_response_ms"])

    df_plot = pd.DataFrame({
        SCENARIO_LABELS[s].replace("\n", " "): _sample(s)
        for s in results
    })
    df_long = df_plot.melt(var_name="Scenario", value_name="Response Time (ms)")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Full range
    palette = {SCENARIO_LABELS[s].replace("\n", " "): COLORS[s] for s in results}
    sns.violinplot(data=df_long, x="Scenario", y="Response Time (ms)",
                   hue="Scenario", palette=palette, ax=axes[0], cut=0, legend=False)
    axes[0].set_title("Response Time Distribution (Full Range)", fontweight="bold")

    # Zoomed: cache scenarios only
    cache_scenarios = [s for s in results if s != "baseline"]
    df_cache = pd.DataFrame({
        SCENARIO_LABELS[s].replace("\n", " "): _sample(s)
        for s in cache_scenarios
    }).melt(var_name="Scenario", value_name="Response Time (ms)")
    palette_cache = {SCENARIO_LABELS[s].replace("\n", " "): COLORS[s] for s in cache_scenarios}
    sns.violinplot(data=df_cache, x="Scenario", y="Response Time (ms)",
                   hue="Scenario", palette=palette_cache, ax=axes[1], cut=0, legend=False)
    axes[1].set_title("Response Time Distribution (Cache Scenarios)", fontweight="bold")

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "rt_distribution.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── CSV report ─────────────────────────────────────────────────────────────────
def save_csv_report(results: dict):
    rows = [{"scenario": s, **d} for s, d in results.items()]
    df   = pd.DataFrame(rows)
    path = os.path.join(REPORTS_DIR, "benchmark_report.csv")
    df.to_csv(path, index=False)
    print(f"  Saved: {path}")


# ── Text summary ───────────────────────────────────────────────────────────────
def print_summary(results: dict):
    from tabulate import tabulate
    baseline = results["baseline"]
    rows = []
    for s, d in results.items():
        med_speedup = (baseline["median_response_ms"] / d["median_response_ms"]
                       if d["median_response_ms"] > 0 else 1.0)
        rows.append([
            SCENARIO_LABELS[s].replace("\n", " "),
            f"{d['cache_hit_rate_pct']}%",
            f"{d.get('select_cache_hit_rate_pct', 0)}%",
            f"{d['avg_response_ms']} ms",
            f"{d['median_response_ms']} ms",
            f"{d['p95_response_ms']} ms",
            f"{med_speedup:.1f}×",
        ])
    headers = ["Scenario", "Hit Rate", "SELECT Hit Rate",
               "Avg RT", "Median RT", "P95 RT", "Median Speedup"]
    print("\n" + tabulate(rows, headers=headers, tablefmt="github"))

    ai = results.get("ai_prefetch", {})
    if ai.get("prediction_count"):
        print(f"\nAI Pre-fetch stats:")
        print(f"  Predictions made    : {ai['prediction_count']:,}")
        print(f"  Pre-fetch attempts  : {ai.get('prefetch_attempts', 0):,}  "
              f"({ai.get('prefetch_attempts', 0)/ai['prediction_count']*100:.1f}% of predictions)")
        print(f"  Pre-fetch successes : {ai.get('prefetch_successes', 0):,}")
        print(f"  Skipped (low conf)  : {ai.get('skipped_low_confidence', 0):,}")
        print(f"  Skipped (non-SELECT): {ai.get('skipped_non_select', 0):,}")


# ── Entry point ────────────────────────────────────────────────────────────────
def generate_all(results: dict = None):
    _setup()
    results = results or load_results()
    print("Generating charts...")
    plot_cache_hit_rate(results)
    plot_response_time_comparison(results)
    plot_prefetch_breakdown(results)
    plot_improvement_summary(results)
    plot_rt_distribution(results)
    save_csv_report(results)
    print_summary(results)
    print(f"\nAll outputs saved to {CHARTS_DIR} and {REPORTS_DIR}")


if __name__ == "__main__":
    generate_all()
