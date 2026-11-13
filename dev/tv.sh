# Reach the TV. Sourced by build-and-install.sh and the dev/ scripts that talk to a TV; it is not run on its own.
#
# Settings are lines NAME=value in dev/local.env (git ignores that file); a value already set in the environment wins.
#   TV_HOST      the TV's address, with or without :port (required)
#   CLEANYOURTV  a checkout of cleanyourtv with tools/venv (optional). When set, its ADB client is used; otherwise
#                the stock adb is (platform-tools on the PATH, port 5555 unless TV_HOST names one).
#
# Defines:
#   tv CMD...          run a shell command on the TV and print its output
#   tv_install APK     install the APK
#   tv_screenshot FILE save a screenshot as a PNG

_TV_ENV="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/local.env"
if [ -f "$_TV_ENV" ]; then
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in ''|'#'*) continue ;; esac
    case "$_line" in *=*) ;; *) continue ;; esac
    _name="${_line%%=*}"; _value="${_line#*=}"
    _value="${_value//\$HOME/$HOME}"
    case "$_name" in *[!A-Za-z0-9_]*|'') continue ;; esac
    [ -n "${!_name:-}" ] || export "$_name=$_value"
  done < "$_TV_ENV"
fi
unset _line _name _value
: "${TV_HOST:?set TV_HOST or write it into dev/local.env}"
export TV_HOST

if [ -n "${CLEANYOURTV:-}" ]; then
  _TV_PY="$CLEANYOURTV/tools/venv/bin/python"
  [ -x "$_TV_PY" ] || { echo "CLEANYOURTV is set but $_TV_PY is missing: point it at a checkout of cleanyourtv with tools/venv (python3 -m venv tools/venv && tools/venv/bin/pip install -r tools/requirements.txt), or unset it to use adb" >&2; return 1 2>/dev/null || exit 1; }
  tv_run() { "$_TV_PY" -I "$CLEANYOURTV/tools/tv.py" "$@"; }
  tv_install() {
    "$_TV_PY" -I "$CLEANYOURTV/tools/b64push.py" "$1" /data/local/tmp/littlereddog.apk >/dev/null
    tv_run "pm install -r /data/local/tmp/littlereddog.apk; rm -f /data/local/tmp/littlereddog.apk"
  }
  tv_screenshot() { "$_TV_PY" -I "$CLEANYOURTV/tools/tv.py" --screenshot "$1"; }
else
  command -v adb >/dev/null || { echo "adb not found: install the Android platform tools, or set CLEANYOURTV" >&2; return 1 2>/dev/null || exit 1; }
  case "$TV_HOST" in *:*) _TV_TARGET="$TV_HOST" ;; *) _TV_TARGET="$TV_HOST:5555" ;; esac
  adb connect "$_TV_TARGET" >/dev/null || { echo "adb connect $_TV_TARGET failed" >&2; return 1 2>/dev/null || exit 1; }
  tv_run() { adb -s "$_TV_TARGET" shell "$@"; }
  tv_install() { adb -s "$_TV_TARGET" install -r "$1"; }
  tv_screenshot() { adb -s "$_TV_TARGET" exec-out screencap -p > "$1" && echo "saved $1"; }
fi
tv() { tv_run "$@"; }
