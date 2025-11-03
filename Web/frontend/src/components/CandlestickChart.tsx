import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

export default function CandlestickChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chart = createChart(chartContainerRef.current!, { width: 600, height: 320 });
    const candleSeries = chart.addCandlestickSeries();
    candleSeries.setData([
      { time: '2025-10-12', open: 100, high: 120, low: 90, close: 110 },
      { time: '2025-10-13', open: 110, high: 130, low: 105, close: 128 },
    ]);
    return () => chart.remove();
  }, []);

  return <div ref={chartContainerRef} />;
}