export type ApiErrorBody = {
  code: string;
  message: string;
  details?: unknown;
};

export type ApiEnvelope<T> = {
  success: boolean;
  data: T | null;
  error: ApiErrorBody | null;
  request_id: string;
};

export class ApiError extends Error {
  code: string;
  details?: unknown;
  requestId?: string;
  status?: number;

  constructor(
    message: string,
    options: {
      code?: string;
      details?: unknown;
      requestId?: string;
      status?: number;
    } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = options.code ?? 'request_failed';
    this.details = options.details;
    this.requestId = options.requestId;
    this.status = options.status;
  }
}

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type AuthStatus = {
  authenticated: boolean;
  password_required: boolean;
};

export type DashboardAccount = {
  user_id: string;
  phone: string | null;
  nickname: string;
  real_name: string | null;
  avatar_url: string;
  active: boolean;
  last_login_at: string | null;
  login_count?: number;
  created_at: string | null;
  updated_at: string | null;
  school?: string | null;
  stage_name?: string | null;
  subject_name?: string | null;
  join_unit_time?: number | null;
  account_type?: number | null;
};

export type UpstreamUserProfile = {
  user_id: string;
  phone: string | null;
  nickname: string;
  real_name: string | null;
  avatar_url: string;
  school?: string | null;
  stage_name?: string | null;
  subject_name?: string | null;
};

export type AccountVerification = {
  verification_token: string;
  expires_at: string;
  profile: UpstreamUserProfile;
};

export type LoginEvent = {
  id: number;
  user_id: string | null;
  username: string;
  status: string;
  error_code: string | null;
  ip_address: string;
  created_at: string;
};

export type LoginEventSummary = {
  counts: Record<string, number>;
};

export type LoginEventTrendPoint = {
  time: string;
  count: number;
};

export type ServiceStatus = {
  status: string;
  listen_port?: number | null;
};

export type ServiceCommandResult = {
  accepted: boolean;
  action: 'restart' | 'stop';
};

export type SettingsSnapshot = {
  network: {
    api_port: number;
    dashboard_host: string;
    dashboard_port: number;
  };
  runtime: {
    enable_eventlog: boolean;
    auto_restart_on_crash: boolean;
    restart_delay_seconds: number;
  };
  authentication: {
    dashboard_password_required: boolean;
    session_ttl_seconds: number;
    enable_password_error_disable: boolean;
    password_set?: boolean;
    force_password_for_host?: boolean;
    is_loopback?: boolean;
  };
  encryption: {
    key_source: 'environment' | 'dpapi';
    key_version: number;
  };
};

export type SettingsPatchResponse = {
  settings: SettingsSnapshot;
  restart_required: boolean;
};

export type EncryptionRotateResult = {
  rotated: number;
  key_source: 'environment' | 'dpapi';
  key_version: number;
};

export type AccountListParams = {
  page?: number;
  page_size?: number;
  q?: string;
  active?: boolean | null;
};

export type LoginEventListParams = {
  page?: number;
  page_size?: number;
  status?: string | null;
  user_id?: string | null;
};

export type StreamEvent =
  | { type: 'service.snapshot'; data: { status?: string } }
  | {
      type: 'login.event';
      data: {
        username?: string;
        user_id?: string | null;
        status?: string;
        error_code?: string | null;
      };
    };

export type SetupStatus = {
  oobe_completed: boolean;
  encryption_ready: boolean;
  key_source: 'environment' | 'dpapi';
  key_version: number;
};

export type EncryptionSetupResult = {
  ok: boolean;
  key_source: string;
  key_version: number;
  key: string | null;
};
