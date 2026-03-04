export interface Article {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content?: string;
  category: string;
  tags: string[];
  author: string;
  cover_image_url: string;
  source_url: string;
  source_type: string;
  published_at: string;
  created_at: string;
  read_time_minutes: number;
}

export interface PaginationInfo {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ArticlesResponse {
  articles: Article[];
  pagination: PaginationInfo;
  meta: {
    generated_at: string;
  };
}

export interface CategoryInfo {
  name: string;
  count: number;
  slug: string;
}

export interface PriceData {
  btc_usd: number;
  gold_usd: number;
  silver_usd: number;
  updated_at: string;
}
