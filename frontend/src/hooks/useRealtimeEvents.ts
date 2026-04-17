import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { RealtimeEvent } from '../types';


const REALTIME_BASE = (import.meta.env.VITE_REALTIME_BASE || 'http://localhost:8010').replace(/\/$/, '');
const RETRY_DELAY_MS = 5000;
const INVALIDATION_DELAY_MS = 250;


const invalidateRealtimeQueries = (queryClient: ReturnType<typeof useQueryClient>) => {
  queryClient.invalidateQueries({ queryKey: ['scrapers'] });
  queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
  queryClient.invalidateQueries({ queryKey: ['activeMonitor'] });
  queryClient.invalidateQueries({ queryKey: ['stats'] });
  queryClient.invalidateQueries({ queryKey: ['history'] });
  queryClient.invalidateQueries({ queryKey: ['recentJobs'] });
  queryClient.invalidateQueries({ queryKey: ['managedJobs'] });
  queryClient.invalidateQueries({ queryKey: ['scrapedRecords'] });
  queryClient.invalidateQueries({ queryKey: ['systemMetrics'] });
};


export const useRealtimeEvents = (enabled: boolean, token: string | null) => {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryTimeoutRef = useRef<number | null>(null);
  const invalidateTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || !token) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (retryTimeoutRef.current !== null) {
        window.clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      return undefined;
    }

    let disposed = false;

    const scheduleInvalidation = () => {
      if (invalidateTimeoutRef.current !== null) {
        return;
      }

      invalidateTimeoutRef.current = window.setTimeout(() => {
        invalidateTimeoutRef.current = null;
        invalidateRealtimeQueries(queryClient);
      }, INVALIDATION_DELAY_MS);
    };

    const connect = () => {
      if (disposed) {
        return;
      }

      const streamUrl = `${REALTIME_BASE}/events?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (message) => {
        let payload: RealtimeEvent | null = null;
        try {
          payload = JSON.parse(message.data) as RealtimeEvent;
        } catch {
          return;
        }

        if (!payload || payload.type === 'heartbeat' || payload.type === 'connected') {
          return;
        }

        if (payload.type === 'job_event') {
          scheduleInvalidation();
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        if (eventSourceRef.current === eventSource) {
          eventSourceRef.current = null;
        }

        if (!disposed && retryTimeoutRef.current === null) {
          retryTimeoutRef.current = window.setTimeout(() => {
            retryTimeoutRef.current = null;
            connect();
          }, RETRY_DELAY_MS);
        }
      };
    };

    connect();

    return () => {
      disposed = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (retryTimeoutRef.current !== null) {
        window.clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      if (invalidateTimeoutRef.current !== null) {
        window.clearTimeout(invalidateTimeoutRef.current);
        invalidateTimeoutRef.current = null;
      }
    };
  }, [enabled, queryClient, token]);
};