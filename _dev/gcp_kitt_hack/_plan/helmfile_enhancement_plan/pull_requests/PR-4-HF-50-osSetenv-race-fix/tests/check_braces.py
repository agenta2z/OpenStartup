#!/usr/bin/env python3
"""Crude brace-balance check on Go source. Skips strings + comments."""
import sys

def check(path):
    src = open(path).read()
    i = 0
    in_str = None    # None or the quote char
    in_line_cmt = False
    in_blk_cmt = False
    ch_open = ch_close = 0
    while i < len(src):
        c = src[i]
        n = src[i+1] if i+1 < len(src) else ''
        if in_line_cmt:
            if c == '\n': in_line_cmt = False
            i += 1; continue
        if in_blk_cmt:
            if c == '*' and n == '/': in_blk_cmt = False; i += 2; continue
            i += 1; continue
        if in_str:
            if c == '\\' and in_str != '`':  # escapes don't apply in raw strings
                i += 2; continue
            if c == in_str:
                in_str = None
            i += 1; continue
        if c == '/' and n == '/': in_line_cmt = True; i += 2; continue
        if c == '/' and n == '*': in_blk_cmt = True; i += 2; continue
        if c in ('"', "'", '`'): in_str = c; i += 1; continue
        if c == '{': ch_open += 1
        elif c == '}': ch_close += 1
        i += 1
    print(f"{{={ch_open} }}={ch_close}", file=sys.stderr)
    return 0 if ch_open == ch_close else 1

if __name__ == "__main__":
    sys.exit(check(sys.argv[1]))
