#!/data/data/com.termux/files/usr/bin/bash
# ONE-TIME. Makes the permanent app signing key and saves the 4 secrets into GitHub.
# Run from the repo root in Termux:  pkg install openjdk-17 gh -y && gh auth login && bash android-wrapper/setup-signing.sh
set -e
command -v keytool >/dev/null || { echo "Run: pkg install openjdk-17"; exit 1; }
command -v gh >/dev/null || { echo "Run: pkg install gh && gh auth login"; exit 1; }
KS="$HOME/spacexbot-release.jks"
if [ ! -f "$KS" ]; then
  PASS=$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)
  keytool -genkeypair -keystore "$KS" -alias spacexbot -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass "$PASS" -keypass "$PASS" -dname "CN=spaceXBot, O=spaceXBot, C=KE" >/dev/null 2>&1
  echo "$PASS" > "$HOME/spacexbot-release.pass"; chmod 600 "$HOME/spacexbot-release.pass" "$KS"
else
  PASS=$(cat "$HOME/spacexbot-release.pass") || { echo "Key exists but no password file. Stop."; exit 1; }
fi
gh secret set ANDROID_KEYSTORE_PASSWORD -b "$PASS"
gh secret set ANDROID_KEY_PASSWORD -b "$PASS"
gh secret set ANDROID_KEY_ALIAS -b "spacexbot"
base64 -w0 "$KS" | gh secret set ANDROID_KEYSTORE_BASE64
echo "Done. BACK UP $KS and $HOME/spacexbot-release.pass somewhere private. Never commit them."
