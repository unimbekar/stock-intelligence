"use client";

import { CandlestickSeries, ColorType, createChart, type IChartApi } from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { Bar } from "@/lib/market";

export function PriceChart({ bars }: { bars: Bar[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const styles = getComputedStyle(document.documentElement);
    const background = styles.getPropertyValue("--elevated").trim() || "#181d23";
    const text = styles.getPropertyValue("--muted").trim() || "#9aa3ae";
    const line = styles.getPropertyValue("--line").trim() || "#313a46";
    const chart: IChartApi = createChart(node, {
      autoSize: true,
      height: 420,
      layout: { background: { type: ColorType.Solid, color: background }, textColor: text },
      grid: { vertLines: { color: line }, horzLines: { color: line } },
      rightPriceScale: { borderColor: line },
      timeScale: { borderColor: line, rightOffset: 2 },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#3dbe86",
      downColor: "#f07178",
      borderVisible: false,
      wickUpColor: "#3dbe86",
      wickDownColor: "#f07178",
    });
    series.setData(
      bars.map((bar) => ({
        time: bar.session,
        open: Number(bar.open),
        high: Number(bar.high),
        low: Number(bar.low),
        close: Number(bar.close),
      })),
    );
    const fit = () => {
      chart.timeScale().setVisibleLogicalRange({ from: 0, to: Math.max(bars.length - 1, 1) });
    };
    fit();
    const frame = requestAnimationFrame(fit);
    return () => {
      cancelAnimationFrame(frame);
      chart.remove();
    };
  }, [bars]);

  return <div ref={ref} className="h-[420px] w-full" />;
}
