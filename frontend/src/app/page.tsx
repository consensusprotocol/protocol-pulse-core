import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-24 text-center">
      <h1 className="text-4xl md:text-6xl font-bold mb-6">
        <span className="text-[#CC0000]">Protocol</span> Pulse
      </h1>
      <p className="text-[#888888] text-lg md:text-xl mb-12 max-w-2xl mx-auto">
        World-class Bitcoin intelligence. Real-time analysis, market signals,
        and investigative reporting for transactors.
      </p>
      <Link
        href="/articles"
        className="inline-block bg-[#CC0000] text-white px-8 py-3 rounded font-semibold transition-all duration-200 hover:bg-[#CC0000]/80"
      >
        Read Latest Intel
      </Link>
    </div>
  );
}
