import axios, { type AxiosError, type AxiosInstance } from 'axios';
import {
  type AccountListParams,
  type AccountVerification,
  type ApiEnvelope,
  ApiError,
  type AuthStatus,
  type DashboardAccount,
  type EncryptionRotateResult,
  type EncryptionSetupResult,
  type LoginEvent,
  type LoginEventListParams,
  type LoginEventSummary,
  type LoginEventTrendPoint,
  type Page,
  type ServiceCommandResult,
  type ServiceStatus,
  type SettingsPatchResponse,
  type SettingsSnapshot,
  type SetupStatus,
} from './types';

export function unwrap<T>(envelope: ApiEnvelope<T>): T {
  if (envelope?.success) {
    return envelope.data as T;
  }
  const error = envelope?.error;
  throw new ApiError(error?.message || '请求失败', {
    code: error?.code || 'request_failed',
    details: error?.details,
    requestId: envelope?.request_id,
  });
}

export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiEnvelope<unknown>>;
    const envelope = axiosError.response?.data;
    if (envelope && typeof envelope === 'object' && 'success' in envelope) {
      return new ApiError(
        envelope.error?.message || axiosError.message || '请求失败',
        {
          code: envelope.error?.code || 'request_failed',
          details: envelope.error?.details,
          requestId: envelope.request_id,
          status: axiosError.response?.status,
        },
      );
    }
    return new ApiError(axiosError.message || '网络请求失败', {
      code: axiosError.code || 'network_error',
      status: axiosError.response?.status,
    });
  }
  if (error instanceof Error) {
    return new ApiError(error.message, { code: 'unknown_error' });
  }
  return new ApiError('未知错误', { code: 'unknown_error' });
}

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { Accept: 'application/json' },
});

http.interceptors.response.use(
  (response) => {
    response.data = unwrap(response.data as ApiEnvelope<unknown>);
    return response;
  },
  (error) => {
    const normalized = normalizeError(error);
    if (normalized.status === 401) {
      unauthorizedHandler?.();
    }
    return Promise.reject(normalized);
  },
);

async function get<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const response = await http.get(path, { params: cleanParams(params) });
  return response.data as T;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const response = await http.post(path, body ?? {});
  return response.data as T;
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  const response = await http.patch(path, body ?? {});
  return response.data as T;
}

async function del<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const response = await http.delete(path, { params: cleanParams(params) });
  return response.data as T;
}

function cleanParams(
  params?: Record<string, unknown>,
): Record<string, unknown> | undefined {
  if (!params) {
    return undefined;
  }
  const next: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') {
      continue;
    }
    next[key] = value;
  }
  return next;
}

export const api = {
  authStatus: () => get<AuthStatus>('/auth/status'),
  login: (password: string) => post<AuthStatus>('/auth/login', { password }),
  logout: () => post<AuthStatus>('/auth/logout'),

  verifyAccount: (account: string, password: string) =>
    post<AccountVerification>('/accounts/verify', { account, password }),
  createAccount: (verification_token: string) =>
    post<DashboardAccount>('/accounts', { verification_token }),
  listAccounts: (params: AccountListParams = {}) =>
    get<Page<DashboardAccount>>('/accounts', {
      page: params.page,
      page_size: params.page_size,
      q: params.q,
      active: params.active,
    }),
  enableAccount: (userId: string) =>
    post<DashboardAccount>(`/accounts/${encodeURIComponent(userId)}/enable`),
  disableAccount: (userId: string) =>
    post<DashboardAccount>(`/accounts/${encodeURIComponent(userId)}/disable`),
  refreshAccount: (userId: string) =>
    post<DashboardAccount>(`/accounts/${encodeURIComponent(userId)}/refresh`),
  deleteAccount: (userId: string) =>
    del<{ deleted: boolean }>(`/accounts/${encodeURIComponent(userId)}`, {
      confirm: true,
    }),

  listLoginEvents: (params: LoginEventListParams = {}) =>
    get<Page<LoginEvent>>('/login-events', {
      page: params.page,
      page_size: params.page_size,
      status: params.status,
      user_id: params.user_id,
    }),
  loginEventSummary: (hours = 24) =>
    get<LoginEventSummary>('/login-events/summary', { hours }),
  loginEventTrends: (hours = 24) =>
    get<LoginEventTrendPoint[]>('/login-events/trends', { hours }),
  pruneLoginEvents: (before: string) =>
    del<{ deleted: number }>('/login-events', { before }),

  getSettings: () => get<SettingsSnapshot>('/settings'),
  patchSettings: (body: {
    network?: Partial<SettingsSnapshot['network']>;
    runtime?: Partial<SettingsSnapshot['runtime']>;
    authentication?: Partial<SettingsSnapshot['authentication']>;
  }) => patch<SettingsPatchResponse>('/settings', body),
  rotateEncryption: (key_source: 'environment' | 'dpapi') =>
    post<EncryptionRotateResult>('/security/encryption/rotate', { key_source }),

  serviceStatus: () => get<ServiceStatus>('/service/status'),
  restartService: () => post<ServiceCommandResult>('/service/restart'),
  stopService: () => post<ServiceCommandResult>('/service/stop'),

  setupStatus: () => get<SetupStatus>('/setup/status'),
  listKeyPreview: async (): Promise<string | null> => {
    const res = await get<{ key?: string }>('/setup/encryption/key-preview');
    return res?.key ?? null;
  },
  setupEncryption: (body: {
    mode: 'generate' | 'custom';
    key_source: 'environment' | 'dpapi';
    custom_key?: string | null;
  }) => post<EncryptionSetupResult>('/setup/encryption', body),
  changeDashboardPassword: (password: string) =>
    post<AuthStatus>('/auth/login', { password }),
};

export { http };
