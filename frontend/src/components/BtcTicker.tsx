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
      <div className="flex items-center gap-2 text-sm bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] rounded-lg px-3 py-1.5">
        <span className="text-[#888888] font-mono text-xs">BTC</span>
        <span className="text-[#888888] font-mono">---</span>
      </div>
    );
  }

  const isPositive = state.change24h >= 0;
  const changeColor = isPositive ? "text-emerald-400" : "text-red-400";
  const glowColor = isPositive
    ? "drop-shadow-[0_0_6px_rgba(52,211,153,0.3)]"
    : "drop-shadow-[0_0_6px_rgba(248,113,113,0.3)]";
  const changePrefix = isPositive ? "+" : "";

  return (
    <div
      className={`flex items-center gap-2 text-sm bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] rounded-lg px-3 py-1.5 ${
        state.pulsing ? "animate-price-pulse" : ""
      }`}
    >
      <span className="text-[#888888] font-mono text-xs tracking-wider">BTC</span>
      <span className="text-[#EDEDED] font-semibold font-mono tabular-nums">
        ${state.price.toLocaleString("en-US", { maximumFractionDigits: 0 })}
      </span>
      <span className={`${changeColor} ${glowColor} text-xs font-medium font-mono tabular-nums`}>
        {changePrefix}{state.change24h.toFixed(1)}%
      </span>
    </div>
  );
}
