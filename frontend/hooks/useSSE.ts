'use client';

import { useEffect, useRef, useCallback } from 'react';

interface UseSSEOptions {
  url: string;
  events: string[];
  onEvent: (event: string, data: any) => void;
  onError?: (error: Event) => void;
  enabled?: boolean;
}

export function useSSE({
  url,
  events,
  onEvent,
  onError,
  enabled = true,
}: UseSSEOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  const onErrorRef = useRef(onError);

  // Keep refs up to date
  onEventRef.current = onEvent;
  onErrorRef.current = onError;

  const connect = useCallback(() => {
    if (!enabled) return;

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    events.forEach((eventType) => {
      eventSource.addEventListener(eventType, ((e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          onEventRef.current(eventType, data);
        } catch {
          onEventRef.current(eventType, e.data);
        }
      }) as EventListener);
    });

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      onErrorRef.current?.(error);
    };

    return eventSource;
  }, [url, events, enabled]);

  useEffect(() => {
    const eventSource = connect();

    return () => {
      eventSource?.close();
      eventSourceRef.current = null;
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  return { disconnect };
}
