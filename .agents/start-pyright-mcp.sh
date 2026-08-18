#!/bin/sh

set -eu

cache_root="${XDG_CACHE_HOME:-${HOME}/.cache}/python-harness/mcp"
mcp_bin="$cache_root/bin/mcp-language-server"
pyright_bin="$cache_root/pyright/bin/pyright-langserver"

if [ ! -x "$mcp_bin" ]; then
    mkdir -p "$cache_root/bin"
    GOBIN="$cache_root/bin" go install github.com/isaacphi/mcp-language-server@v0.1.1
fi

if [ ! -x "$pyright_bin" ]; then
    mkdir -p "$cache_root/pyright"
    npm install --global --prefix "$cache_root/pyright" pyright@1.1.413 >&2
fi

exec "$mcp_bin" --workspace . --lsp "$pyright_bin" -- --stdio
