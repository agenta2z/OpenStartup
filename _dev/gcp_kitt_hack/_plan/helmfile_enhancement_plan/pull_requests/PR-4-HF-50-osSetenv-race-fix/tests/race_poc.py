#!/usr/bin/env python3
"""HF-50 race proof-of-concept (offline, no Go toolchain required).

Models the os.Setenv race using Python threads (the bug + fix logic is
language-agnostic: any process-wide mutable global with concurrent set/read
exhibits this bug).

Without --with-mutex: reproduces the bug (cross-thread token contamination).
With    --with-mutex: demonstrates the fix.

Exit codes:
  0 = expected outcome observed
  1 = unexpected outcome (test infrastructure broken)
"""
import argparse, os, sys, threading

# Process-wide "env" simulating Go's os.Setenv/Getenv
_ENV = {}
_ENV_LOCK = threading.Lock()

def setenv(k, v): _ENV[k] = v
def getenv(k):    return _ENV.get(k, "")
def unsetenv(k):  _ENV.pop(k, None)

def activity(idx, use_mutex, mismatch_counter):
    my_token = f"token-{idx}"
    if use_mutex:
        with _ENV_LOCK:
            setenv("DTE_SLAUTH_TOKEN", my_token)
            try:
                # Simulate downstream helpers.go reads.
                for _ in range(50):
                    got = getenv("DTE_SLAUTH_TOKEN")
                    if got != my_token:
                        mismatch_counter[0] += 1
            finally:
                unsetenv("DTE_SLAUTH_TOKEN")
    else:
        setenv("DTE_SLAUTH_TOKEN", my_token)
        try:
            for _ in range(50):
                got = getenv("DTE_SLAUTH_TOKEN")
                if got != my_token:
                    mismatch_counter[0] += 1
        finally:
            unsetenv("DTE_SLAUTH_TOKEN")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--with-mutex", action="store_true")
    p.add_argument("--no-mutex", action="store_true")
    p.add_argument("--expect-race", action="store_true")
    p.add_argument("--expect-no-race", action="store_true")
    p.add_argument("--threads", type=int, default=200)
    args = p.parse_args()

    use_mutex = args.with_mutex
    mismatches = [0]
    threads = [threading.Thread(target=activity, args=(i, use_mutex, mismatches)) for i in range(args.threads)]
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"threads={args.threads} use_mutex={use_mutex} mismatches={mismatches[0]}", file=sys.stderr)
    if args.expect_race:
        # Without mutex, mismatches should be > 0 (bug observed).
        sys.exit(0 if mismatches[0] > 0 else 1)
    if args.expect_no_race:
        # With mutex, mismatches must be 0 (bug absent).
        sys.exit(0 if mismatches[0] == 0 else 1)
    sys.exit(0)

if __name__ == "__main__":
    main()
