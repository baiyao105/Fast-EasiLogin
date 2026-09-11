import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AccountListParams, LoginEventListParams } from '@/lib/types';

export const dashboardKeys = {
  auth: ['auth-status'] as const,
  service: ['service'] as const,
  accounts: (params: AccountListParams) => ['accounts', params] as const,
  accountSummary: ['accounts-summary'] as const,
  loginEvents: (params: LoginEventListParams) =>
    ['login-events', params] as const,
  loginSummary: (hours: number) => ['login-summary', hours] as const,
  loginTrends: (hours: number) => ['login-trends', hours] as const,
  settings: ['settings'] as const,
};

export function useAuthStatus() {
  return useQuery({
    queryKey: dashboardKeys.auth,
    queryFn: api.authStatus,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (password: string) => api.login(password),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.auth });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: async () => {
      queryClient.clear();
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.auth });
    },
  });
}

export function useServiceStatus(enabled = true) {
  return useQuery({
    queryKey: dashboardKeys.service,
    queryFn: api.serviceStatus,
    enabled,
    refetchInterval: 30_000,
  });
}

export function useAccounts(params: AccountListParams) {
  return useQuery({
    queryKey: dashboardKeys.accounts(params),
    queryFn: () => api.listAccounts(params),
  });
}

export function useAccountSummary() {
  return useQuery({
    queryKey: dashboardKeys.accountSummary,
    queryFn: async () => {
      const [all, active] = await Promise.all([
        api.listAccounts({ page: 1, page_size: 1 }),
        api.listAccounts({ page: 1, page_size: 1, active: true }),
      ]);
      return { total: all.total, active: active.total };
    },
  });
}

export function useLoginSummary(hours = 24) {
  return useQuery({
    queryKey: dashboardKeys.loginSummary(hours),
    queryFn: () => api.loginEventSummary(hours),
  });
}

export function useLoginTrends(hours = 24) {
  return useQuery({
    queryKey: dashboardKeys.loginTrends(hours),
    queryFn: () => api.loginEventTrends(hours),
  });
}

export function useLoginEvents(params: LoginEventListParams) {
  return useQuery({
    queryKey: dashboardKeys.loginEvents(params),
    queryFn: () => api.listLoginEvents(params),
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (verificationToken: string) =>
      api.createAccount(verificationToken),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['accounts'] }),
        queryClient.invalidateQueries({
          queryKey: dashboardKeys.accountSummary,
        }),
      ]);
    },
  });
}

export function useRefreshAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.refreshAccount(userId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['accounts'] }),
        queryClient.invalidateQueries({
          queryKey: dashboardKeys.accountSummary,
        }),
      ]);
    },
  });
}

export function useToggleAccountActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, active }: { userId: string; active: boolean }) =>
      active ? api.enableAccount(userId) : api.disableAccount(userId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['accounts'] }),
        queryClient.invalidateQueries({
          queryKey: dashboardKeys.accountSummary,
        }),
      ]);
    },
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.deleteAccount(userId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['accounts'] }),
        queryClient.invalidateQueries({
          queryKey: dashboardKeys.accountSummary,
        }),
      ]);
    },
  });
}

export function usePruneLoginEvents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (before: string) => api.pruneLoginEvents(before),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['login-events'] }),
        queryClient.invalidateQueries({ queryKey: ['login-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['login-trends'] }),
      ]);
    },
  });
}

export function useSettings() {
  return useQuery({
    queryKey: dashboardKeys.settings,
    queryFn: api.getSettings,
  });
}

export function usePatchSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.patchSettings,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.settings });
    },
  });
}

export function useRotateEncryption() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key_source: 'environment' | 'dpapi') =>
      api.rotateEncryption(key_source),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.settings });
    },
  });
}

export function useRestartService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.restartService(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.service });
    },
  });
}

export function useStopService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.stopService(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.service });
    },
  });
}
