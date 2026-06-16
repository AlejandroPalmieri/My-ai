#!/bin/sh
set -eu

repo_url="${AGENTOS_REPO_URL:-https://github.com/AlejandroPalmieri/My-ai.git}"
install_root="${AGENTOS_INSTALL_ROOT:-$HOME/.agentos/source}"
bin_dir="${AGENTOS_BIN_DIR:-$HOME/.local/bin}"
binary_path="$bin_dir/agentos"
source_dir="${AGENTOS_SOURCE_DIR:-}"
profile_path="${AGENTOS_PROFILE_PATH:-$HOME/.profile}"
shell_rc_path="${AGENTOS_SHELL_RC_PATH:-$HOME/.bashrc}"

add_path_block() {
  target="$1"
  path_to_add="$2"
  marker_start="# >>> agentos path >>>"
  marker_end="# <<< agentos path <<<"
  mkdir -p "$(dirname "$target")"
  if [ -f "$target" ] && grep -F "$marker_start" "$target" >/dev/null 2>&1; then
    return 0
  fi
  {
    printf '\n%s\n' "$marker_start"
    printf 'export PATH="%s:$PATH"\n' "$path_to_add"
    printf '%s\n' "$marker_end"
  } >> "$target"
}

if ! command -v go >/dev/null 2>&1; then
  echo "Go 1.22+ is required to install AgentOS Go CLI." >&2
  exit 1
fi

if [ -n "$source_dir" ]; then
  install_root="$source_dir"
elif command -v git >/dev/null 2>&1; then
  if [ -d "$install_root/.git" ]; then
    git -C "$install_root" pull --ff-only
  else
    mkdir -p "$(dirname "$install_root")"
    git clone "$repo_url" "$install_root"
  fi
else
  echo "git is required to install AgentOS from source." >&2
  exit 1
fi

mkdir -p "$bin_dir"
go build -C "$install_root" -o "$binary_path" ./cmd/agentos

echo "AgentOS Go CLI installed at $binary_path"
case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *)
    add_path_block "$profile_path" "$bin_dir"
    add_path_block "$shell_rc_path" "$bin_dir"
    echo "Added $bin_dir to PATH in $profile_path and $shell_rc_path"
    echo "Open a new terminal or run: export PATH=\"$bin_dir:\$PATH\""
    ;;
esac

if command -v "$binary_path" >/dev/null 2>&1; then
  "$binary_path" version
fi
