import { useEffect, useState } from 'react';
import { fetchBackendHealth } from '../lib/api';

export function useBackendStatus() {
  const [isReady, setIsReady] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let timeoutId: NodeJS.Timeout;

    async function checkHealth() {
      if (cancelled) return;

      try {
        const healthy = await fetchBackendHealth();
        if (!cancelled) {
          setIsReady(healthy);
          
          if (healthy) {
            // Only stop checking when backend is ready
            setIsChecking(false);
          } else {
            // Keep checking indicator active during retries
            timeoutId = setTimeout(checkHealth, 2000);
          }
        }
      } catch {
        if (!cancelled) {
          setIsReady(false);
          // Keep retrying
          timeoutId = setTimeout(checkHealth, 2000);
        }
      }
    }

    checkHealth();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  return { isReady, isChecking };
}

