#!/usr/bin/env bash
# Отправляет коммиты текущей ветки в GitHub — только если репозиторий закрыт для посторонних.
#
#   bash tools/git_push_checked.sh
#
# Перед отправкой каждого коммита проверяет без входа, что репозиторий не виден: API отвечает 404,
# адрес git — 401. Если он открыт, отправка не делается (в проекте чужие персональные данные и
# проекты жалоб; правило — в CLAUDE.md, раздел «Резервная копия в GitHub»).
# Коммиты уходят по одному, от старого к новому: GitHub не принимает отправку больше 2 ГБ.
# Адрес репозитория берётся из настроек git (git remote get-url origin), в файлах проекта его нет.
set -uo pipefail
cd "$(dirname "$0")/.."
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never

url=$(git remote get-url origin)
path=$(printf '%s' "$url" | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##')
if [ -z "$path" ] || [ "$path" = "$url" ]; then
  echo "не удалось разобрать адрес репозитория GitHub"; exit 2
fi
branch=$(git rev-parse --abbrev-ref HEAD)

closed() {
  local api smart
  api=$(curl -s -o /dev/null -w "%{http_code}" -H "Accept: application/vnd.github+json" "https://api.github.com/repos/$path")
  smart=$(curl -s -o /dev/null -w "%{http_code}" "https://github.com/$path.git/info/refs?service=git-upload-pack")
  echo "  видимость без входа: API $api, git $smart"
  [ "$api" = "404" ] && [ "$smart" = "401" ]
}

remote_head=$(git ls-remote origin "refs/heads/$branch" 2>/dev/null | cut -f1)
if [ -n "$remote_head" ]; then
  if ! git cat-file -e "$remote_head" 2>/dev/null; then
    echo "в GitHub есть коммиты, которых нет локально: сначала разобраться (git fetch), отправка не сделана"; exit 5
  fi
  range="$remote_head..$branch"
else
  range="$branch"
fi
commits=$(git rev-list --reverse "$range")
if [ -z "$commits" ]; then
  echo "отправлять нечего: в GitHub уже $(git rev-parse --short "$branch")"
  exit 0
fi
count=0
for commit in $commits; do
  short=$(git rev-parse --short "$commit")
  echo "== $short | $(git log -1 --format=%s "$commit" | cut -c1-80)"
  if ! closed; then
    echo "ОСТАНОВКА: репозиторий виден без входа. Отправка не сделана; видимость меняет владелец репозитория."
    exit 3
  fi
  if ! git push origin "$commit:refs/heads/$branch" 2>&1 | tr '\r' '\n' | grep -v -E '^(Writing|Counting|Compressing|Enumerating|Delta) objects: +[0-9]+% ' | tail -n 8; then :; fi
  if [ "$(git ls-remote origin "refs/heads/$branch" | cut -f1)" != "$commit" ]; then
    echo "  повтор по HTTP/1.1"
    git -c http.version=HTTP/1.1 -c http.postBuffer=524288000 push origin "$commit:refs/heads/$branch" 2>&1 | tr '\r' '\n' | tail -n 8
    if [ "$(git ls-remote origin "refs/heads/$branch" | cut -f1)" != "$commit" ]; then
      echo "ОШИБКА: коммит $short не отправлен"; exit 4
    fi
  fi
  count=$((count + 1))
done
git fetch -q origin 2>/dev/null || true
echo "готово: отправлено коммитов — $count; в GitHub $(git ls-remote origin "refs/heads/$branch" | cut -c1-12), локально $(git rev-parse "$branch" | cut -c1-12)"
