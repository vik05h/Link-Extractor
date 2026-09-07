export interface PartItem {
  index: number;
  url: string;
  direct_url?: string;
  filename?: string;
  size?: string;
  status: 'pending' | 'decrypting' | 'resolved' | 'failed';
  excluded?: boolean;
  category?: 'core' | 'language' | 'optional';
}

export interface GameRecord {
  slug: string;
  title: string;
  image_url: string;
  source_url: string;
  total_parts: number;
  total_size_str: string;
  total_size_bytes?: number;
  timestamp_utc: string;
  local_time?: string;
  age_str?: string;
  freshness?: 'fresh' | 'aging' | 'expired';
  uploader?: string;
  health_status?: string;
  health_color?: string;
  used_count?: number;
}

export interface HistoryRecord {
  id: number;
  game_title: string;
  source_url?: string;
  parts_count?: number;
  total_size?: string;
  created_at?: string;
  resolved_links: string[];
}

export interface AppSettings {
  concurrency?: number;
  auto_validate?: boolean;
  jd_port?: number;
  community_auto_upload?: boolean;
  clipboard_sentinel_enabled?: boolean;
  auto_crash_reporting?: boolean;
}

export interface DetectedClip {
  url: string;
  url_type: string;
  slug: string;
}

export interface IssueComment {
  id: string;
  author_name?: string;
  author_type: 'admin' | 'reporter' | 'gamer';
  text: string;
  screenshot_data?: string;
  created_at: string;
  app_version?: string;
}

export interface IssueReport {
  id: string;
  subject: string;
  category: string;
  description: string;
  screenshot_data?: string;
  status: 'open' | 'investigating' | 'fixed' | 'closed';
  affected_users_count: number;
  admin_remark?: string;
  created_at: string;
  app_version?: string;
  os_info?: string;
  user_voted?: boolean;
  comments?: Record<string, IssueComment> | IssueComment[];
  comments_count?: number;
}

