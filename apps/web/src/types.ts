// API 응답 타입 — contracts/*.yaml 에서 화면이 쓰는 필드만 옮겼다. 계약이 바뀌면 여기도 맞춘다.

export type Market = "KRX" | "US" | "CRYPTO" | "INDEX";
export type Horizon = 5 | 20 | 60;
export type Stance = "bull" | "bear" | "neutral";
export type Category = "stock" | "crypto";

export interface Paged<T> { items: T[]; next_cursor?: string | null }

// ── youtube ──
export interface ChannelOut {
  channel_id: string; anon_code: string; title: string; handle: string; category: Category | string;
  subscriber_count?: number | null; tracked: boolean; added_at: string;
}
export interface YoutubeCoverage {
  channels: number; videos: number; first_published: string | null; last_published: string | null; by_category: Record<string, number>;
}

// ── mentions ──
export interface MentionsCoverage {
  videos_seen: number; videos_matched: number; match_rate: number; mentions: number; assets: number;
  by_stance?: Partial<Record<Stance, number>>; last_video_at: string | null;
}
export interface TrendingItem { asset_id: string; mentions: number; prev_mentions: number; channels: number; views: number; last_mentioned_at: string }
export interface UnmatchedOut { video_id: string; channel_id: string; title: string; published_at: string }

// ── market-data ──
export interface AssetName {
  asset_id: string; name: string; market: Market | string; symbol: string; asset_type: string;
  benchmark_id?: string | null; aliases?: string[];
}
export interface PriceOut { asset_id: string; trade_date: string; close: number; volume?: number | null; currency: string }
export interface DisclosureOut { rcept_no: string; asset_id: string; rcept_dt: string; report_nm: string; kind: string }
export interface MarketCoverage {
  assets_by_market: Record<string, { total: number; tracked: number; theme?: number }>;
  prices: number; prices_with_volume: number; last_trade_date: string | null;
  disclosures: number; disclosure_assets: number; last_disclosure_date: string | null;
}

// ── stats ──
export interface HistBucket { from: number; to: number; n: number }
// summarize() 결과 (services/stats/engine.py). n=0 이면 horizon·n·low_sample 만 온다.
export interface Summary {
  horizon: number; n: number; low_sample: boolean;
  mean?: number; median?: number; win_rate?: number; p10?: number; p90?: number;
  excess_mean?: number | null; excess_n?: number; excess_win_rate?: number | null;
  vol_ratio_median?: number | null; vol_up_rate?: number | null; vol_n?: number;
  disclosure_rate?: number | null; disclosure_n?: number;
  histogram?: HistBucket[];
  assets_n?: number; assets_up?: number; asset_win_rate?: number;  // 채널 요약에만
}
export interface SummaryOut { key: string; value: Summary; updated_at: string }
export interface EventOut {
  mention_id: number; asset_id: string; channel_id: string; market: string; kind?: string; stance?: Stance | string;
  stance_words?: string | null; published_at: string; t0_date: string | null; t0_close: number | null;
  r5: number | null; r20: number | null; r60: number | null; x5: number | null; x20: number | null; x60: number | null;
  vol_ratio?: number | null; near_disclosure?: boolean | null;
}
export type RankMetric = "excess_mean" | "mean" | "win_rate" | "asset_win_rate";
export interface ChannelRank {
  channel_id: string; n: number; mean: number; median: number; win_rate: number;
  excess_mean: number | null; excess_win_rate: number | null; vol_ratio_median: number | null;
  assets_n?: number | null; assets_up?: number | null; asset_win_rate?: number | null;
}
export interface ChannelRanking { horizon: number; metric: string; stance?: string; min_n: number; top: ChannelRank[]; bottom: ChannelRank[]; all: ChannelRank[] }
export interface StatsCoverage {
  events: number; events_theme: number; with_t0: number; r5_filled: number; r20_filled: number; r60_filled: number;
  vol_ratio_filled: number; disclosure_checked: number; last_computed_at: string | null; summaries: number;
}

export interface Problem { type?: string; title?: string; status?: number; detail?: string; instance?: string }

// 화면 이동 — App 의 해시 라우터로 간다 (#tab/arg)
export type Go = (tab: string, arg?: string) => void;
