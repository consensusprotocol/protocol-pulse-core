import Link from "next/link";
import { fetchArticles } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";

export default async function Home() {
  const data = await fetchArticles(1, 6);
  const articles = data?.articles ?? [];

  return (
    <div>
      {/* Hero */}
      <section className="relative py-28 md:py-40 overflow-hidden mesh-gradient-1">
        {/* Ambient glow orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#CC0000]/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-[#CC0000]/[0.02] rounded-full blur-[100px]" />

        <div className="max-w-7xl mx-auto px-4 text-center relative">
          <div className="animate-fade-in-up">
            <div className="flex items-center justify-center gap-2 mb-6">
              <span className="pulse-dot" />
              <span className="text-[10px] uppercase tracking-[0.25em] text-[#CC0000] font-semibold">
                Live Intelligence Feed
              </span>
            </div>
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight">
              <span className="text-[#CC0000] drop-shadow-[0_0_30px_rgba(204,0,0,0.3)]">
                Protocol
              </span>{" "}
              Pulse
            </h1>
          </div>
          <p className="text-[#888888] text-lg md:text-xl mb-10 max-w-2xl mx-auto leading-relaxed animate-fade-in-up-delay-1">
            World-class Bitcoin intelligence. Real-time analysis, market
            signals, and investigative reporting for transactors.
          </p>
          <div className="animate-fade-in-up-delay-2">
            <Link
              href="/articles"
              className="inline-block bg-[#CC0000] text-white px-8 py-3.5 rounded-lg font-semibold transition-all duration-500 hover:shadow-[0_0_40px_rgba(204,0,0,0.4)] hover:-translate-y-0.5 hover:bg-[#CC0000]/90"
            >
              Read Latest Intel
            </Link>
          </div>
        </div>
      </section>

      {/* Latest articles */}
      {articles.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 pb-20 relative">
          <div className="flex items-center justify-between mb-8 animate-fade-in-up-delay-3">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold">Latest Intel</h2>
              <div className="w-16 h-[3px] bg-[#CC0000] mt-3 rounded-full shadow-[0_0_10px_rgba(204,0,0,0.3)]" />
            </div>
            <Link
              href="/articles"
              className="text-[#CC0000] hover:text-[#FF4444] hover:drop-shadow-[0_0_8px_rgba(204,0,0,0.3)] text-sm font-medium transition-all duration-300"
            >
              View All &rarr;
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
