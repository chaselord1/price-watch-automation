"""Renders a dashboard image from price_history.csv: price lines with target
levels and alert markers, current status table, alert log, and summary cards.

Run:
  python dashboard.py                    -> dashboard.png from price_history.csv
  python dashboard.py sample_history.csv -> from a different history file
"""
import sys
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from price_watch import WATCHES

BG, PANEL, GRID, TXT, MUTED = "#0f1419", "#161c24", "#2a323d", "#e6e9ee", "#8a94a3"
COLORS = ["#4cc9f0", "#f4a261", "#90be6d", "#e76f51", "#c77dff", "#ffd166"]
targets = {w["name"]: w["target"] for w in WATCHES}


def card(ax, label, value, sub=""):
    ax.set_facecolor(PANEL); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.text(0.06, 0.72, label, color=MUTED, fontsize=10, transform=ax.transAxes)
    ax.text(0.06, 0.32, value, color=TXT, fontsize=20, weight="bold", transform=ax.transAxes)
    if sub:
        ax.text(0.06, 0.08, sub, color=MUTED, fontsize=9, transform=ax.transAxes)


def main(path="price_history.csv"):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    if "target" not in df.columns:            # live log has no target column; sample file does
        df["target"] = df["product"].map(targets)
    targets.update(df.groupby("product")["target"].last().to_dict())
    df["below"] = df["price"] < df["target"]

    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    gs = fig.add_gridspec(3, 4, height_ratios=[0.8, 3, 2.2], hspace=0.62, wspace=0.25,
                          left=0.045, right=0.88, top=0.90, bottom=0.06)
    fig.text(0.045, 0.955, "Price Watch", color=TXT, fontsize=20, weight="bold")
    fig.text(0.045, 0.925, f"{len(df['product'].unique())} products tracked · "
             f"{len(df)} checks · last run {df['timestamp'].max():%Y-%m-%d %H:%M}",
             color=MUTED, fontsize=10)

    # summary cards
    latest = df.groupby("product").tail(1).set_index("product")
    first = df.groupby("product").head(1).set_index("product")["price"]
    chg = ((latest["price"] - first) / first * 100)
    n_alerts = int(df["below"].sum())
    card(fig.add_subplot(gs[0, 0]), "PRODUCTS", str(len(latest)), "watch list")
    card(fig.add_subplot(gs[0, 1]), "CHECKS LOGGED", str(len(df)),
         f"every {__import__('price_watch').CHECK_MINUTES} min")
    card(fig.add_subplot(gs[0, 2]), "BELOW TARGET NOW", str(int(latest["below"].sum())),
         f"{n_alerts} alert emails sent total")
    card(fig.add_subplot(gs[0, 3]), "BIGGEST DROP", f"{chg.min():+.1f}%",
         chg.idxmin() if len(chg) else "")

    # price chart
    ax = fig.add_subplot(gs[1, :3]); ax.set_facecolor(PANEL)
    for i, (name, g) in enumerate(df.groupby("product")):
        c = COLORS[i % len(COLORS)]
        ax.plot(g["timestamp"], g["price"], color=c, lw=2, marker="o", ms=3, label=name)
        ax.axhline(targets.get(name, float("nan")), color=c, ls="--", lw=1, alpha=0.5)
        hits = g[g["below"]]
        ax.scatter(hits["timestamp"], hits["price"], color="#ff5c5c", s=55, zorder=5,
                   edgecolor=BG)
    ax.scatter([], [], color="#ff5c5c", s=55, label="alert sent (below target)")
    ax.plot([], [], color=MUTED, ls="--", label="target price")
    ax.set_title("Price history vs target", color=TXT, loc="left", fontsize=12)
    ax.grid(color=GRID, lw=0.6); ax.tick_params(colors=MUTED)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TXT, fontsize=8.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.14), ncol=4, frameon=False)

    # % change bars
    ax2 = fig.add_subplot(gs[1, 3]); ax2.set_facecolor(PANEL)
    short = [n[:18] for n in chg.index]
    bars = ax2.barh(short, chg.values,
                    color=["#ff5c5c" if v < 0 else "#90be6d" for v in chg.values])
    ax2.axvline(0, color=MUTED, lw=0.8); ax2.yaxis.tick_right()
    ax2.set_title("Change since first check", color=TXT, loc="left", fontsize=12)
    ax2.tick_params(colors=MUTED, labelsize=8); ax2.grid(color=GRID, lw=0.6, axis="x")
    for s in ax2.spines.values():
        s.set_color(GRID)
    for b, v in zip(bars, chg.values):
        ax2.text(0.3 if v < 0 else -0.3, b.get_y() + b.get_height() / 2, f"{v:+.1f}%",
                 va="center", ha="left" if v < 0 else "right", color=TXT, fontsize=8, transform=ax2.get_yaxis_transform(), clip_on=False)

    # status table
    ax3 = fig.add_subplot(gs[2, :2]); ax3.set_facecolor(PANEL); ax3.axis("off")
    ax3.set_title("Current status", color=TXT, loc="left", fontsize=12)
    rows = [[n[:34], f"{r.price:.2f}", f"{r.target:.2f}",
             f"{(r.price - r.target) / r.target * 100:+.1f}%",
             "BELOW TARGET" if r.below else "watching"] for n, r in latest.iterrows()]
    t = ax3.table(cellText=rows, colLabels=["Product", "Price", "Target", "vs target", "Status"],
                  loc="upper center", cellLoc="left", colLoc="left",
                  colWidths=[0.40, 0.13, 0.13, 0.15, 0.19])
    t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.6)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID); cell.set_facecolor(PANEL if r else "#1f2733")
        cell.get_text().set_color(TXT if r else MUTED)
        if r and c == 4 and rows[r - 1][4] == "BELOW TARGET":
            cell.get_text().set_color("#ff5c5c")

    # alert log
    ax4 = fig.add_subplot(gs[2, 2:]); ax4.set_facecolor(PANEL); ax4.axis("off")
    ax4.set_title("Alert log (email)", color=TXT, loc="left", fontsize=12)
    log = df[df["below"]].sort_values("timestamp", ascending=False).head(7)
    lines = [f"{r.timestamp:%b %d %H:%M}   {r['product'][:26]:<26}  {r.price:>7.2f}  (target {r.target:.2f})"
             for _, r in log.iterrows()] or ["no alerts yet"]
    ax4.text(0.02, 0.92, "\n".join(lines), family="monospace", fontsize=9, color=TXT,
             va="top", transform=ax4.transAxes, linespacing=1.7)

    fig.savefig("dashboard.png", dpi=110, facecolor=BG)
    print("wrote dashboard.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "price_history.csv")
