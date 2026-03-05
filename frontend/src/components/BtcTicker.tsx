"use client";

import { useEffect, useState } from "react";

interface PriceState {
  price: number;
  change24h: number;
  loading: boolean;
  pulsing: boolean;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://protocolpulse.replit.app";

export default function BtcTicker() {
  const [state, setState] = useState<PriceState>({
    price: 0,
    change24h: 0,
    loading: true,
    pulsing: false,
  });

  useEffect(() => {
    async function fetchPrice() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/v2/prices`);
        if (!res.ok) return;
        const data = await res.json();
        const btc = data.prices?.bitcoin;
        if (!btc) return;

        setState((prev) => ({
          price: btc.price,
          change24h: btc.change_24h,
          loading: false,
          pulsing: prev.price !== 0 && prev.price !== btc.price,
        }));

        // Clear pulse after animation
        setTimeout(() => setState((prev) => ({ ...prev, pulsing: false })), 600);
      } catch {
        // Silently fail, keep last known price
      }
    }

    fetchPrice();
    const interval = setInterval(fetchPrice, 60000);
    return () => clearInterval(interval);
  }, []);

  if (state.loading) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="text-[#888888]">BTC</span>
        <span className="text-[#888888]">---</span>
      </div>
    );
  }

  const isPositive = state.change24h >= 0;
  const changeColor = isPositive ? "text-emerald-500" : "text-red-500";
  const changePrefix = isPositive ? "+" : "";

  return (
    <div className={`flex items-center gap-2 text-sm ${state.pulsing ? "animate-price-pulse" : ""}`}>
      <span className="text-[#888888] font-medium">BTC</span>
      <span className="text-[#EDEDED] font-semibold tabular-nums">
        ${state.price.toLocaleString("en-US", { maximumFractionDigits: 0 })}
      </span>
      <span className={`${changeColor} text-xs font-medium tabular-nums`}>
        {changePrefix}{state.change24h.toFixed(1)}%
      </span>
    </div>
  );
}
