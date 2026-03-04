import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
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
        <header className="border-b border-[#1F1F1F] sticky top-0 z-50 bg-[#0A0A0A]/95 backdrop-blur-sm">
          <nav className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <Link href="/" className="text-[#CC0000] font-bold text-xl tracking-wider">
              PROTOCOL PULSE
            </Link>
            <div className="flex items-center gap-6">
              <Link
                href="/"
                className="text-[#888888] hover:text-[#EDEDED] text-sm transition-all duration-200"
              >
                Home
              </Link>
              <Link
                href="/articles"
                className="text-[#888888] hover:text-[#EDEDED] text-sm transition-all duration-200"
              >
                Intel
              </Link>
            </div>
          </nav>
        </header>

        {/* Main content */}
        <main className="flex-1">{children}</main>

        {/* Footer */}
        <footer className="border-t border-[#1F1F1F] mt-auto">
          <div className="max-w-7xl mx-auto px-4 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-[#888888] text-sm">
              &copy; {new Date().getFullYear()} Protocol Pulse. All rights reserved.
            </p>
            <div className="flex items-center gap-4 text-sm">
              <a
                href="https://twitter.com/ProtocolPulse"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#888888] hover:text-[#EDEDED] transition-all duration-200"
              >
                Twitter
              </a>
              <a
                href="https://nostr.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#888888] hover:text-[#EDEDED] transition-all duration-200"
              >
                Nostr
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
