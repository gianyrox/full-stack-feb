#!/bin/bash
# Export all Claude Code sessions with secret redaction
set -euo pipefail

SRC="$HOME/.claude/projects"
DEST="$(pwd)/claude-sessions"

mkdir -p "$DEST"

# Map project directory names to human-readable names
declare -A PROJECT_NAMES=(
  ["-home-gian"]="home"
  ["-home-gian-DerbyFish-derbyfish-gtm"]="derbyfish-gtm"
  ["-home-gian-enterprise-ai"]="enterprise-ai"
  ["-home-gian-Projects"]="projects-root"
  ["-home-gian-Projects-full-stack-feb"]="full-stack-feb"
  ["-home-gian-Projects-scriva"]="scriva"
)

# Copy and redact each project
for project_dir in "$SRC"/*/; do
  dirname=$(basename "$project_dir")
  friendly_name="${PROJECT_NAMES[$dirname]:-$dirname}"

  echo "Processing: $friendly_name ($dirname)"
  dest_dir="$DEST/$friendly_name"
  mkdir -p "$dest_dir"

  # Copy all JSONL files (main sessions)
  find "$project_dir" -maxdepth 1 -name "*.jsonl" -exec cp {} "$dest_dir/" \;

  # Copy subagent sessions if they exist
  if find "$project_dir" -path "*/subagents/*.jsonl" -print -quit 2>/dev/null | grep -q .; then
    find "$project_dir" -path "*/subagents/*.jsonl" | while read -r agent_file; do
      session_id=$(basename "$(dirname "$(dirname "$agent_file")")")
      agent_dest="$dest_dir/subagents-$session_id"
      mkdir -p "$agent_dest"
      cp "$agent_file" "$agent_dest/"
    done
  fi

  # Copy memory files if they exist
  if [ -d "$project_dir/memory" ]; then
    cp -r "$project_dir/memory" "$dest_dir/memory"
  fi
done

# Also copy the global history
cp "$HOME/.claude/history.jsonl" "$DEST/global-history.jsonl" 2>/dev/null || true

echo ""
echo "Redacting secrets..."

# Redaction patterns - match actual secret VALUES, not just key names
# Using perl for better regex support
find "$DEST" -name "*.jsonl" -o -name "*.md" | while read -r f; do
  perl -i -pe '
    # OpenAI API keys (sk-... pattern, 40+ chars)
    s/sk-[a-zA-Z0-9]{20,}/sk-[REDACTED]/g;

    # OpenAI project keys
    s/sk-proj-[a-zA-Z0-9_-]{20,}/sk-proj-[REDACTED]/g;

    # Slack bot tokens
    s/xoxb-[a-zA-Z0-9\-]+/xoxb-[REDACTED]/g;

    # Slack user tokens
    s/xoxp-[a-zA-Z0-9\-]+/xoxp-[REDACTED]/g;

    # GitHub personal access tokens
    s/ghp_[a-zA-Z0-9]{36}/ghp_[REDACTED]/g;

    # GitHub OAuth tokens
    s/gho_[a-zA-Z0-9]{36}/gho_[REDACTED]/g;

    # Bearer tokens in headers
    s/(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}/$1\[REDACTED]/g;

    # Generic long hex/base64 tokens after common env var patterns
    # Matches: OPENAI_API_KEY=abc123... or "OPENAI_API_KEY": "abc123..."
    s/((?:API_KEY|SECRET_KEY|SECRET|ACCESS_TOKEN|AUTH_TOKEN|PRIVATE_KEY|CLIENT_SECRET)["\s]*[:=]["\s]*)([a-zA-Z0-9_\-\.\/\+]{20,})/$1\[REDACTED]/gi;

    # Anthropic API keys
    s/sk-ant-[a-zA-Z0-9\-]{20,}/sk-ant-[REDACTED]/g;

    # AWS keys
    s/AKIA[A-Z0-9]{16}/AKIA[REDACTED]/g;

    # Supabase keys (long JWT-like strings after supabase patterns)
    s/(supabase[^"]*(?:key|token|secret)["\s]*[:=]["\s]*)([a-zA-Z0-9_\-\.]{30,})/$1\[REDACTED]/gi;

    # Generic password values in JSON
    s/("password"\s*:\s*")[^"]{4,}(")/\$1\[REDACTED]\$2/gi;

    # SSH private keys (entire key block)
    s/-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----/[SSH-KEY-REDACTED]/g;

    # SSH public key values (ssh-rsa AAAA..., ssh-ed25519 AAAA...)
    s/(ssh-(?:rsa|ed25519|dss|ecdsa)\s+)[A-Za-z0-9+\/=]{40,}/$1\[REDACTED]/g;

    # .env file values: KEY=value patterns (common env var names)
    s/((?:DATABASE_URL|DB_PASSWORD|DB_HOST|REDIS_URL|MONGO_URI|JWT_SECRET|SESSION_SECRET|COOKIE_SECRET|ENCRYPTION_KEY|SENDGRID_API_KEY|TWILIO_AUTH_TOKEN|STRIPE_SECRET_KEY|STRIPE_PUBLISHABLE_KEY|NEXT_PUBLIC_SUPABASE_ANON_KEY|SUPABASE_SERVICE_ROLE_KEY|FIREBASE_API_KEY|VERCEL_TOKEN|NETLIFY_AUTH_TOKEN|HEROKU_API_KEY|DIGITALOCEAN_TOKEN|CLOUDFLARE_API_TOKEN|SENTRY_DSN|DATADOG_API_KEY|NEW_RELIC_LICENSE_KEY|SLACK_BOT_TOKEN|SLACK_SIGNING_SECRET|DISCORD_TOKEN|TELEGRAM_BOT_TOKEN|WEBHOOK_SECRET)["\s]*[:=]["\s]*)([^\s"\\]{8,})/$1\[REDACTED]/gi;

    # Email addresses (personal info)
    s/[a-zA-Z0-9._%+\-]+\@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/[EMAIL-REDACTED]/g;

    # IP addresses (v4, private ranges too)
    s/\b(?:\d{1,3}\.){3}\d{1,3}\b/[IP-REDACTED]/g;

    # JWT tokens (three base64 segments separated by dots)
    s/eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}/[JWT-REDACTED]/g;

    # Hex strings that look like secrets (32+ hex chars, likely hashes/tokens)
    s/(?<=[=:\s"'\''])[0-9a-f]{40,}(?=[,\s"'\''}\]\n])/[HEX-REDACTED]/gi;

    # AWS secret access keys (40 char base64)
    s/(aws_secret_access_key\s*[:=]\s*)[a-zA-Z0-9\/+=]{40}/$1\[REDACTED]/gi;

    # Google API keys
    s/AIza[a-zA-Z0-9_\-]{35}/AIza[REDACTED]/g;

    # Vercel tokens
    s/(VERCEL_[A-Z_]*["\s]*[:=]["\s]*)([a-zA-Z0-9_\-]{20,})/$1\[REDACTED]/gi;

    # npm tokens
    s/npm_[a-zA-Z0-9]{36}/npm_[REDACTED]/g;

    # GitHub fine-grained PAT tokens
    s/github_pat_[a-zA-Z0-9_]{30,}/github_pat_[REDACTED]/g;

    # Generic GITHUB_TOKEN values
    s/(GITHUB_TOKEN\s*[:=]\s*)[^\s"\\]{10,}/$1\[REDACTED]/gi;

    # Contentful tokens (relevant to this project)
    s/(CONTENTFUL_[A-Z_]*["\s]*[:=]["\s]*)([a-zA-Z0-9_\-]{20,})/$1\[REDACTED]/gi;
  ' "$f"
done

echo "Done!"
echo ""
echo "Summary:"
find "$DEST" -name "*.jsonl" | wc -l
echo " session files exported"
du -sh "$DEST"
