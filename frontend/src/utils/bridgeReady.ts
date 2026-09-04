/**
 * bridgeReady.ts — Resilient pywebview RPC Bridge Readiness Utility.
 * 
 * Ensures frontend components safely wait for exposed Python methods
 * before executing RPC calls, eliminating startup race conditions.
 */

export function isBridgeMethodReady(methodName?: string): boolean {
  if (typeof window === 'undefined') return false;
  const api = (window as any).pywebview?.api;
  if (!api) return false;
  if (!methodName) return true;
  return typeof api[methodName] === 'function';
}

export function waitForBridge(methodName?: string, timeoutMs: number = 8000): Promise<boolean> {
  if (typeof window === 'undefined') {
    return Promise.resolve(false);
  }

  // If already fully initialized and method exists, resolve synchronously
  if (isBridgeMethodReady(methodName)) {
    return Promise.resolve(true);
  }

  return new Promise<boolean>((resolve) => {
    let resolved = false;
    let pollInterval: any = null;
    let timeoutTimer: any = null;

    const cleanup = () => {
      resolved = true;
      window.removeEventListener('pywebviewready', onReady);
      if (pollInterval) clearInterval(pollInterval);
      if (timeoutTimer) clearTimeout(timeoutTimer);
    };

    const tryResolve = () => {
      if (!resolved && isBridgeMethodReady(methodName)) {
        cleanup();
        resolve(true);
        return true;
      }
      return false;
    };

    const onReady = () => {
      // Allow microscopic tick for _createApi definition if fired simultaneously
      if (!tryResolve()) {
        setTimeout(tryResolve, 20);
      }
    };

    window.addEventListener('pywebviewready', onReady);

    // Fast backup polling (50ms) to catch situations where pywebviewready fired
    // before listener was bound or across async module boundaries
    pollInterval = setInterval(() => {
      tryResolve();
    }, 50);

    timeoutTimer = setTimeout(() => {
      if (!resolved) {
        cleanup();
        console.warn(`[Bridge] Timed out waiting for bridge method '${methodName || 'api'}' (${timeoutMs}ms)`);
        resolve(false);
      }
    }, timeoutMs);
  });
}
