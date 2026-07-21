export type BDRole = "bd" | "admin";
export type ClientStatus = "active" | "paused" | "placed" | "churned";
export type ProfileType = "resume" | "linkedin";
export type RemoteType = "fully_remote" | "hybrid" | "onsite" | "unknown";
export type ScrapeStatus = "pending" | "running" | "success" | "failed";
export type AnalysisStatus = "pending" | "running" | "complete" | "failed";
export type ApplicationStatus = "applied" | "screening" | "interview" | "offer" | "rejected";

export interface BD {
  id: string;
  email: string;
  full_name: string;
  role: BDRole;
  created_at: string;
}

export interface Client {
  id: string;
  bd_id: string;
  full_name: string;
  email: string;
  current_city: string | null;
  current_state: string | null;
  current_country: string | null;
  timezone: string | null;
  status: ClientStatus;
  created_at: string;
}

export interface ResumeExtraction {
  full_name: string | null;
  email: string | null;
  current_city: string | null;
  current_state: string | null;
  current_country: string | null;
  raw_text: string;
}

export interface TargetRole {
  id: string;
  client_id: string;
  title: string;
  seniority: string | null;
  must_have_keywords: string[];
  created_at: string;
}

export interface Profile {
  id: string;
  client_id: string;
  target_role_id: string | null;
  type: ProfileType;
  variant_label: string;
  source_url: string | null;
  raw_text: string | null;
  structured_data: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface JobSource {
  id: string;
  name: string;
  is_enabled: boolean;
  rate_limit_per_min: number | null;
}

export interface ScrapeRun {
  id: string;
  job_source_id: string;
  filters: Record<string, unknown>;
  status: ScrapeStatus;
  jobs_found_count: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Job {
  id: string;
  job_source_id: string;
  external_id: string;
  title: string;
  company: string | null;
  location_raw: string | null;
  remote_type: RemoteType;
  country: string | null;
  description: string | null;
  apply_url: string | null;
  posted_at: string | null;
  scraped_at: string;
}

export interface KeywordAnalysis {
  id: string;
  profile_id: string;
  target_role_id: string | null;
  extracted_keywords: string[];
  missing_keywords: string[];
  ats_score: number;
  recruiter_attention_score: number;
  created_at: string;
}

export interface LocationAnalysis {
  id: string;
  client_id: string;
  target_role_id: string | null;
  location_penalty_score: number;
  recommendation: string;
  created_at: string;
}

export interface ProfileScoreDetail {
  profile_id: string;
  strengths: string[];
  weaknesses: string[];
  score: number;
}

export interface ComparisonRun {
  id: string;
  client_id: string;
  target_role_id: string | null;
  profile_ids: string[];
  status: AnalysisStatus;
  result_summary: string | null;
  result_detail: {
    profile_scores?: ProfileScoreDetail[];
    bottlenecks?: string[];
  };
  winner_profile_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Application {
  id: string;
  client_id: string;
  profile_id: string;
  job_id: string;
  applied_at: string;
  status: ApplicationStatus;
  status_updated_at: string;
  notes: string | null;
}

export interface ProfilePerformance {
  profile_id: string;
  variant_label: string;
  total_applications: number;
  status_counts: Record<string, number>;
  interview_rate: number | null;
}
