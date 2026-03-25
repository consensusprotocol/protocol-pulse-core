import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import BtcTicker from "@/components/BtcTicker";
import MobileMenu from "@/components/MobileMenu";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Protocol Pulse",
  description: "World-class Bitcoin intelligence",
  icons: {
    icon: "/favicon.ico",
    apple: "/icon-192.png",
  },
  openGraph: {
    title: "Protocol Pulse",
    description: "World-class Bitcoin intelligence",
    siteName: "Protocol Pulse",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    site: "@ProtocolPulse",
  },
};

const navLinks = [
  { href: "/articles", label: "Intel" },
  { href: "/articles?category=sentiment", label: "Markets" },
  { href: "/articles?category=Mining+Intel", label: "Mining" },
  { href: "/articles?category=opinion", label: "Opinion" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.className} bg-[#0A0A0A] text-[#EDEDED] min-h-screen flex flex-col`}
      >
        {/* Navbar */}
        <header className="sticky top-0 z-50">
          <nav className="bg-black/60 backdrop-blur-xl border-b border-white/[0.06]">
            <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
              <Link
                href="https://protocolpulse.io"
                className="text-[#CC0000] font-bold text-xl tracking-wider flex-shrink-0 hover:drop-shadow-[0_0_12px_rgba(204,0,0,0.5)] transition-all duration-300"
              >
                PROTOCOL PULSE
              </Link>

              {/* Desktop nav */}
              <div className="hidden md:flex items-center gap-8">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="relative text-[#888888] hover:text-[#EDEDED] text-sm font-medium transition-colors duration-200 uppercase tracking-wider group"
                  >
                    {link.label}
                    <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[#CC0000] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  </Link>
                ))}
              </div>

              <div className="flex items-center gap-4">
                <BtcTicker />
                <MobileMenu links={navLinks} />
              </div>
            </div>
          </nav>
          {/* Red gradient accent line under nav */}
          <div className="red-gradient-line" />
        </header>

        {/* Main content */}
        <main className="flex-1">{children}</main>

        {/* Footer */}
        <footer className="mt-auto relative">
          {/* Red gradient accent line at top */}
          <div className="red-gradient-line" />
          <div className="bg-white/[0.02] backdrop-blur-sm border-t border-white/[0.06]">
            <div className="max-w-7xl mx-auto px-4 py-16">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
                {/* Intelligence */}
                <div>
                  <h4 className="text-[#EDEDED] font-semibold text-sm uppercase tracking-wider mb-4">
                    Intelligence
                  </h4>
                  <ul className="space-y-3">
                    <li>
                      <Link
                        href="/articles"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.1)] text-sm transition-all duration-200"
                      >
                        Latest Intel
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/articles?category=sentiment"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.1)] text-sm transition-all duration-200"
                      >
                        Market Sentiment
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/articles?category=Mining+Intel"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.1)] text-sm transition-all duration-200"
                      >
                        Mining Intel
                      </Link>
                    </li>
                  </ul>
                </div>

                {/* Categories */}
                <div>
                  <h4 className="text-[#EDEDED] font-semibold text-sm uppercase tracking-wider mb-4">
                    Categories
                  </h4>
                  <ul className="space-y-3">
                    <li>
                      <Link
                        href="/articles?category=Bitcoin"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.1)] text-sm transition-all duration-200"
                      >
                        Bitcoin
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/articles?category=opinion"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.1)] text-sm transition-all duration-200"
                      >
                        Opinion
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/articles?category=regulation"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.1)] text-sm transition-all duration-200"
                      >
                        Regulation
                      </Link>
                    </li>
                  </ul>
                </div>

                {/* Protocol Pulse */}
                <div>
                  <h4 className="text-[#EDEDED] font-semibold text-sm uppercase tracking-wider mb-4">
                    Protocol Pulse
                  </h4>
                  <ul className="space-y-3">
                    <li>
                      <span className="text-[#888888] text-sm">
                        About
                      </span>
                    </li>
                    <li>
                      <span className="text-[#888888] text-sm">
                        Methodology
                      </span>
                    </li>
                    <li>
                      <span className="text-[#888888] text-sm">
                        Media Kit
                      </span>
                    </li>
                  </ul>
                </div>

                {/* Connect */}
                <div>
                  <h4 className="text-[#EDEDED] font-semibold text-sm uppercase tracking-wider mb-4">
                    Connect
                  </h4>
                  <ul className="space-y-3">
                    <li>
                      <a
                        href="https://twitter.com/ProtocolPulse"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.15)] text-sm transition-all duration-200"
                      >
                        X / Twitter
                      </a>
                    </li>
                    <li>
                      <a
                        href="https://nostr.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.15)] text-sm transition-all duration-200"
                      >
                        Nostr
                      </a>
                    </li>
                    <li>
                      <a
                        href="https://youtube.com/@ProtocolPulse"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.15)] text-sm transition-all duration-200"
                      >
                        YouTube
                      </a>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Halving countdown card */}
              <div className="mb-12 flex justify-center">
                <div className="inline-flex items-center gap-4 bg-white/[0.03] backdrop-blur-md border border-white/[0.06] rounded-xl px-6 py-3">
                  <span className="pulse-dot" />
                  <span className="text-xs uppercase tracking-[0.15em] text-[#888888] font-medium">
                    Next Halving
                  </span>
                  <HalvingCountdown />
                </div>
              </div>

              {/* Bottom bar */}
              <div className="border-t border-white/[0.06] pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
                <span className="text-[#CC0000] font-bold text-sm tracking-wider hover:drop-shadow-[0_0_12px_rgba(204,0,0,0.5)] transition-all duration-300">
                  PROTOCOL PULSE
                </span>
                <p className="text-[#888888] text-xs">
                  &copy; 2026 Protocol Pulse — Intelligence for Transactors
                </p>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

function HalvingCountdown() {
  const halvingDate = new Date("2028-04-15T00:00:00Z");
  const now = new Date();
  const diff = halvingDate.getTime() - now.getTime();
  const days = Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
  const hours = Math.max(0, Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)));

  return (
    <div className="flex items-center gap-2">
      <span className="bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-1 text-[#EDEDED] font-mono text-sm tabular-nums">
        {days}d
      </span>
      <span className="text-[#CC0000] text-xs">:</span>
      <span className="bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-1 text-[#EDEDED] font-mono text-sm tabular-nums">
        {hours}h
      </span>
    </div>
  );
}
