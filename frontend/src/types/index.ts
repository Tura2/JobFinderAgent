export interface Company {
  id: number;
  name: string;
  website: string | null;
  ats_type: string;
  ats_slug: string | null;
  linkedin_url: string | null;
  career_page_url: string | null;
  active: boolean;
  added_at: string;
}

export interface Job {
  id: number;
  title: string;
  url: string;
  description_raw: string | null;
  location: string | null;
  remote: boolean | null;
}

export interface CVVariant {
  id: number;
  name: string;
  file_path: string;
  focus_tags: string;
  is_active: boolean;
}

export interface MatchListItem {
  id: number;
  score: number;
  reasoning: string;
  status: string;
  matched_at: string;
  job_title: string;
  company_name: string;
}

export interface MatchDetail {
  id: number;
  score: number;
  reasoning: string;
  status: string;
  matched_at: string;
  reviewed_at: string | null;
  job: Job;
  company: { id: number; name: string; website: string | null };
  cv_variant: { id: number; name: string; file_path: string; focus_tags: string } | null;
  ambiguous_variants: { id: number; name: string; file_path: string; focus_tags: string }[];
}

export interface Application {
  id: number;
  match_id: number;
  outcome_status: string;
  notes: string | null;
  applied_at: string;
  confirmed_at: string | null;
  job_title: string;
  company_name: string;
  score: number;
}

export interface ScanStatus {
  last_scan_at: string | null;
  next_scan_at: string | null;
  last_scan_new_jobs: number;
  is_running: boolean;
}
