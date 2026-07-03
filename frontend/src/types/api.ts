export interface Account {
  pt_nickname: string;
  pt_appid: string;
  pt_userid: string;
  pt_username: string;
  pt_photourl: string;
}

export interface DashboardStats {
  service_status: string;
  uptime_seconds: number;
  listen_port: number;
  total_logins: number;
  success_logins: number;
  failed_logins: number;
}

export interface Settings {
  Global: {
    port: number;
    webui_port: number;
    enable_eventlog: boolean;
    enable_password_error_disable: boolean;
  };
}

export interface ApiResponse<T> {
  message: string;
  statusCode: string;
  data?: T;
}
