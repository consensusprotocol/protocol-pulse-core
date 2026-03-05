import Link from "next/link";
import { fetchArticles } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";

export default async function Home() {
  const data = await fetchArticles(1, 6);
  const articles = data?.articles ?? [];

  return (
    <div>
      {/* Hero */}
      <section className="relative py-24 md:py-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#CC0000]/5 via-transparent to-transparent" />
        <div className="max-w-7xl mx-auto px-4 text-center relative">
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight">
            <span className="text-[#CC0000]">Protocol</span> Pulse
          </h1>
          <p className="text-[#888888] text-lg md:text-xl mb-10 max-w-2xl mx-auto leading-relaxed">
            World-class Bitcoin intelligence. Real-time analysis, market
            signals, and investigative reporting for transactors.
          </p>
          <Link
            href="/articles"
            className="inline-block bg-[#CC0000] text-white px-8 py-3.5 rounded-lg font-semibold transition-all duration-300 hover:bg-[#CC0000]/90 hover:shadow-[0_0_30px_rgba(204,0,0,0.3)] hover:-translate-y-0.5"
          >
            Read Latest Intel
          </Link>
        </div>
      </section>

      {/* Latest articles */}
      {articles.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 pb-20">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold">Latest Intel</h2>
              <div className="w-12 h-0.5 bg-[#CC0000] mt-2" />
            </div>
            <Link
              href="/articles"
              className="text-[#CC0000] hover:text-[#FF4444] text-sm font-medium transition-colors"
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
