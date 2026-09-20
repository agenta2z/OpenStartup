package main

// HF-50: serialize access to process-wide DTE_* auth env vars.
//
// THE BUG (before this fix):
//   Activity A (cluster X): os.Setenv("DTE_SLAUTH_TOKEN", tokenA);
//                           defer os.Unsetenv("DTE_SLAUTH_TOKEN")
//   Activity B (cluster Y): os.Setenv("DTE_SLAUTH_TOKEN", tokenB);  // overwrites tokenA
//                           defer os.Unsetenv("DTE_SLAUTH_TOKEN")
//   Activity A's downstream HTTP call (helpers.go:202 os.Getenv) reads tokenB
//   -> wrong cluster's auth used -> silent data corruption.
//
// THE FIX:
//   - HealthCheckActivity and ServiceDiscoveryActivity acquire authEnvMu
//     BEFORE setting any DTE_* env vars and hold it for the entire activity
//     lifetime (defer Unlock).
//   - Downstream helpers.go still reads via os.Getenv (no API change).
//   - Tests in auth_env_test.go verify with `go test -race`.
//
// TRADE-OFF (deliberately accepted):
//   Activities serialize while holding tokens. Since each activity is HTTP-bound
//   (kubectl/Argo calls = seconds), this serialization is negligible. The previous
//   "concurrency" silently produced wrong results, so "slower but correct" wins.
//
// CORRECTNESS PROOF SKETCH:
//   - Mutex held across Set + downstream-read window: no other goroutine Sets.
//   - defer order: Unsetenv first (LIFO), then Unlock: env clean before next holder.
//   - Panic-safe: defers fire even on panic, so mutex always released.
//
// Closes: HF-50

import "sync"

// authEnvMu serializes ALL access to process-wide DTE_* auth env vars.
// Acquire BEFORE any os.Setenv("DTE_*", ...) call, hold for the entire
// window in which downstream code may read those vars.
var authEnvMu sync.Mutex
