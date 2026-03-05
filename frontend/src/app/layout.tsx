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
        <header className="border-b border-[#1F1F1F] sticky top-0 z-50 bg-black/80 backdrop-blur-md">
          <nav className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <Link
              href="/"
              className="text-[#CC0000] font-bold text-xl tracking-wider flex-shrink-0"
            >
              PROTOCOL PULSE
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-8">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-[#888888] hover:text-[#EDEDED] text-sm font-medium transition-colors duration-200 uppercase tracking-wider"
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="flex items-center gap-4">
              <BtcTicker />
              <MobileMenu links={navLinks} />
            </div>
          </nav>
        </header>

        {/* Main content */}
        <main className="flex-1">{children}</main>

        {/* Footer */}
        <footer className="border-t border-[#1F1F1F] mt-auto bg-[#0A0A0A]">
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
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      Latest Intel
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/articles?category=sentiment"
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      Market Sentiment
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/articles?category=Mining+Intel"
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
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
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      Bitcoin
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/articles?category=opinion"
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      Opinion
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/articles?category=regulation"
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
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
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      X / Twitter
                    </a>
                  </li>
                  <li>
                    <a
                      href="https://nostr.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      Nostr
                    </a>
                  </li>
                  <li>
                    <a
                      href="https://youtube.com/@ProtocolPulse"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#888888] hover:text-[#EDEDED] text-sm transition-colors"
                    >
                      YouTube
                    </a>
                  </li>
                </ul>
              </div>
            </div>

            {/* Bottom bar */}
            <div className="border-t border-[#1F1F1F] pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="text-[#CC0000] font-bold text-sm tracking-wider">
                  PROTOCOL PULSE
                </span>
                <span className="text-[#1F1F1F]">|</span>
                <HalvingCountdown />
              </div>
              <p className="text-[#888888] text-xs">
                &copy; 2026 Protocol Pulse — Intelligence for Transactors
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

function HalvingCountdown() {
  // Next halving: ~April 2028 (block 1,050,000)
  const halvingDate = new Date("2028-04-15T00:00:00Z");
  const now = new Date();
  const diff = halvingDate.getTime() - now.getTime();
  const days = Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));

  return (
    <span className="text-[#888888] text-xs font-mono">
      Next Halving: ~{days} days
    </span>
  );
}
