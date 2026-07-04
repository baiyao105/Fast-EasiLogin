/**
 * WebSocket 单例管理器
 * 所有组件共享一个连接，避免连接风暴
 */

import { useRef, useEffect, useCallback } from 'react';

type MessageHandler = (data: any) => void;
type Subscriber = {
  id: string;
  onStats?: MessageHandler;
  onRecentLogins?: MessageHandler;
  onLoginTrends?: MessageHandler;
};

interface WebSocketMessage {
  type: string;
  data: any;
}

class WebSocketManager {
  private ws: WebSocket | null = null;
  private subscribers: Map<string, Subscriber> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 20;
  private baseReconnectInterval = 2000;
  private maxReconnectInterval = 30000;
  private shouldReconnect = true;
  private isConnected = false;
  private connectLock = false;

  get connectionState(): boolean {
    return this.isConnected;
  }

  subscribe(subscriber: Subscriber): () => void {
    this.subscribers.set(subscriber.id, subscriber);

    // 如果还没有连接，启动连接
    if (!this.ws && !this.connectLock) {
      this.connect();
    }

    // 返回取消订阅函数
    return () => {
      this.subscribers.delete(subscriber.id);
      // 如果没有订阅者了，关闭连接
      if (this.subscribers.size === 0) {
        this.disconnect();
      }
    };
  }

  /**
   * 更新订阅者的回调函数（不触发重新订阅）
   */
  updateSubscriber(id: string, callbacks: Partial<Omit<Subscriber, 'id'>>): void {
    const subscriber = this.subscribers.get(id);
    if (subscriber) {
      Object.assign(subscriber, callbacks);
    }
  }

  private connect(): void {
    // 防止并发连接
    if (this.connectLock || (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING))) {
      return;
    }

    this.connectLock = true;
    this.shouldReconnect = true;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;

    try {
      this.ws = new WebSocket(`${protocol}//${host}/ws`);
    } catch (e) {
      console.error('WebSocket creation failed:', e);
      this.connectLock = false;
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.isConnected = true;
      this.connectLock = false;
      this.reconnectAttempts = 0;
      console.log('[WS] Connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.dispatch(message);
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    this.ws.onclose = (event) => {
      this.isConnected = false;
      this.connectLock = false;
      this.ws = null;

      const reason = event.reason || 'unknown';
      console.log(`[WS] Disconnected (code: ${event.code}, reason: ${reason})`);

      // 1000 = normal closure, 不重连
      if (event.code === 1000) {
        return;
      }

      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      // onclose 会处理重连，这里不需要额外操作
    };
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WS] Max reconnect attempts reached, giving up');
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;

    // 指数退避 + 随机抖动
    const delay = Math.min(
      this.baseReconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1) + Math.random() * 1000,
      this.maxReconnectInterval
    );

    console.log(`[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private dispatch(message: WebSocketMessage): void {
    for (const subscriber of this.subscribers.values()) {
      try {
        switch (message.type) {
          case 'stats':
            subscriber.onStats?.(message.data);
            break;
          case 'recent_logins':
            subscriber.onRecentLogins?.(message.data);
            break;
          case 'login_trends':
            subscriber.onLoginTrends?.(message.data);
            break;
        }
      } catch (e) {
        console.error('[WS] Subscriber error:', e);
      }
    }
  }

  send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.onclose = null; // 阻止触发重连
      try {
        this.ws.close(1000, 'client disconnect');
      } catch (e) {
        // 忽略关闭异常
      }
      this.ws = null;
    }

    this.isConnected = false;
    this.connectLock = false;
  }

  reconnect(): void {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.shouldReconnect = true;
    this.connect();
  }
}

// 全局单例
const wsManager = new WebSocketManager();

// React Hook
let subscriberIdCounter = 0;

export function useWebSocket(options: {
  onStats?: MessageHandler;
  onRecentLogins?: MessageHandler;
  onLoginTrends?: MessageHandler;
  autoConnect?: boolean;
} = {}) {
  const { onStats, onRecentLogins, onLoginTrends, autoConnect = true } = options;

  const subscriberRef = useRef<string | null>(null);
  const callbacksRef = useRef({ onStats, onRecentLogins, onLoginTrends });

  // 更新回调引用（不触发重新订阅）
  useEffect(() => {
    callbacksRef.current = { onStats, onRecentLogins, onLoginTrends };

    // 如果已经订阅了，更新回调
    if (subscriberRef.current) {
      wsManager.updateSubscriber(subscriberRef.current, {
        onStats,
        onRecentLogins,
        onLoginTrends,
      });
    }
  }, [onStats, onRecentLogins, onLoginTrends]);

  // 只在挂载/卸载时订阅/取消订阅
  useEffect(() => {
    if (!autoConnect) return;

    const id = `sub_${++subscriberIdCounter}`;
    subscriberRef.current = id;

    const unsubscribe = wsManager.subscribe({
      id,
      onStats: callbacksRef.current.onStats,
      onRecentLogins: callbacksRef.current.onRecentLogins,
      onLoginTrends: callbacksRef.current.onLoginTrends,
    });

    return () => {
      unsubscribe();
      subscriberRef.current = null;
    };
  }, [autoConnect]); // 只依赖 autoConnect

  return {
    isConnected: wsManager.connectionState,
    connect: useCallback(() => wsManager.reconnect(), []),
    disconnect: useCallback(() => wsManager.disconnect(), []),
    reconnect: useCallback(() => wsManager.reconnect(), []),
    send: useCallback((msg: any) => wsManager.send(msg), []),
  };
}
