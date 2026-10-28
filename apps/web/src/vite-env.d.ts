/// <reference types="vite/client" />

// .env / .env.production 에서 빌드에 들어가는 주소
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_STATS_URL?: string;
  readonly VITE_MENTIONS_URL?: string;
  readonly VITE_MARKET_DATA_URL?: string;
  readonly VITE_YOUTUBE_URL?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
