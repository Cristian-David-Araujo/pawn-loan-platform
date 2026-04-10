#!/usr/bin/env bash
set -euo pipefail

HEAD_REF="${1:-}"
if [[ -z "$HEAD_REF" ]]; then
  echo "HEAD_REF argument is required" >&2
  exit 1
fi

LATEST_TAG="$(git tag --list 'v*' | sort -V | tail -n 1)"
if [[ -z "$LATEST_TAG" ]]; then
  LATEST_TAG="v0.0.0"
fi

CURRENT_VERSION="${LATEST_TAG#v}"
IFS='.' read -r CUR_MAJOR CUR_MINOR CUR_PATCH <<< "$CURRENT_VERSION"

SEMVER_IN_BRANCH=""
if [[ "$HEAD_REF" =~ ^(release|hotfix)/v?([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  SEMVER_IN_BRANCH="${BASH_REMATCH[2]}"
fi

if [[ -n "$SEMVER_IN_BRANCH" ]]; then
  NEXT_VERSION="$SEMVER_IN_BRANCH"
  BUMP_KIND="explicit"
elif [[ "$HEAD_REF" =~ ^release/ ]]; then
  NEXT_VERSION="${CUR_MAJOR}.$((CUR_MINOR + 1)).0"
  BUMP_KIND="minor"
elif [[ "$HEAD_REF" =~ ^hotfix/ ]]; then
  NEXT_VERSION="${CUR_MAJOR}.${CUR_MINOR}.$((CUR_PATCH + 1))"
  BUMP_KIND="patch"
elif [[ "$HEAD_REF" == "develop" ]]; then
  NEXT_VERSION="${CUR_MAJOR}.$((CUR_MINOR + 1)).0"
  BUMP_KIND="minor_from_develop"
else
  echo "Branch '$HEAD_REF' is not allowed for main release flow (expected release/*, hotfix/*, or develop)." >&2
  exit 1
fi

NEXT_TAG="v${NEXT_VERSION}"

echo "latest_tag=${LATEST_TAG}" >> "$GITHUB_OUTPUT"
echo "version=${NEXT_VERSION}" >> "$GITHUB_OUTPUT"
echo "tag=${NEXT_TAG}" >> "$GITHUB_OUTPUT"
echo "bump_kind=${BUMP_KIND}" >> "$GITHUB_OUTPUT"
