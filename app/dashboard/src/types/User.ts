export type Status =
  | "active"
  | "disabled"
  | "limited"
  | "expired"
  | "on_hold"
  | "error"
  | "connecting"
  | "connected";
export type ProxyKeys = ("vmess" | "vless" | "trojan" | "shadowsocks" | "hysteria")[];
export type ProxyType = {
  vmess?: {
    id?: string;
  };
  vless?: {
    id?: string;
    flow?: string;
  };
  trojan?: {
    password?: string;
  };
  shadowsocks?: {
    password?: string;
    method?: string;
  };
  hysteria?: {
    auth?: string;
    obfs?: string;
    obfs_password?: string;
  };
};

export type DataLimitResetStrategy =
  | "no_reset"
  | "day"
  | "week"
  | "month"
  | "year";

export type UserInbounds = {
  [key: string]: string[];
};
export type ExternalSubscription = {
  id: number;
  name: string;
  url: string;
  update_interval: number;
  is_enabled: boolean;
  last_fetched_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type User = {
  proxies: ProxyType;
  expire: number | null;
  data_limit: number | null;
  data_limit_reset_strategy: DataLimitResetStrategy;
  on_hold_expire_duration: number | null;
  lifetime_used_traffic: number;
  username: string;
  used_traffic: number;
  status: Status;
  links: string[];
  subscription_url: string;
  inbounds: UserInbounds;
  note: string;
  online_at: string;
  sub_last_user_agent: string | null;
  external_subscriptions: ExternalSubscription[];
};

export type UserCreate = Pick<
  User,
  | "inbounds"
  | "proxies"
  | "expire"
  | "data_limit"
  | "data_limit_reset_strategy"
  | "on_hold_expire_duration"
  | "username"
  | "status"
  | "note"
> & {
  external_subscriptions?: number[];
};

export type UserApi = {
  discord_webook: string;
  is_sudo: boolean;
  telegram_id: number | string;
  username: string;
}

export type UserUsageStat = {
  user_id: number;
  username: string;
  bytes_prev_hour: number;
  bytes_curr_hour: number;
  bytes_today: number;
  speed_prev_hour: number;
  speed_curr_hour: number;
  speed_today: number;
};

export type UseGetUserReturn = {
  userData: UserApi;
  getUserIsPending: boolean;
  getUserIsSuccess: boolean;
  getUserIsError: boolean;
  getUserError: Error | null;
}