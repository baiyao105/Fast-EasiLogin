import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { get, post, del } from '../http/client';
import type { Account, DashboardStats, Settings } from '../../types/api';

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => get<{ data: DashboardStats }>('/dashboard/stats')
  });
}

export function useRecentLogins(limit: number = 20) {
  return useQuery({
    queryKey: ['dashboard', 'recent-logins', limit],
    queryFn: () => get<{ data: Array<{ username: string; ip: string; status: string; time: string }> }>(`/dashboard/recent-logins?limit=${limit}`)
  });
}

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: () => get<{ data: Account[] }>('/accounts')
  });
}

export function useAddAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { userid: string; password: string; user_name?: string; head_img?: string }) =>
      post('/accounts', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    }
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userid: string) => del(`/accounts/${userid}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    }
  });
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => get<{ data: Settings }>('/settings')
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<Settings>) => post('/settings', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
  });
}

export function useClearCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => post('/settings/clear-cache'),
    onSuccess: () => {
      queryClient.invalidateQueries();
    }
  });
}
