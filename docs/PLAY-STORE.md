# Kundali on the Google Play Store (Trusted Web Activity)

The web app is already a complete PWA (manifest with id, icons incl. maskable, shortcuts, screenshots; offline service worker),
so the Play Store app is a thin Android wrapper made by PWABuilder — no Android coding.

1. Make sure the latest version is live on https://kundali.vividbrandify.com (open it once on a phone: "Install app" should appear).
2. Open https://www.pwabuilder.com → enter `https://kundali.vividbrandify.com` → **Start**. Scores should be green (manifest, service worker).
3. **Package for stores → Android → Generate package**. Settings:
   - Package ID: `com.vividbrandify.kundali` (choose once; it can never change)
   - App name: `कुंडली — Kundali`, short name `कुंडली`; Signing key: **Create new** (keep the downloaded `signing.keystore` + passwords safe — losing them means you can never update the app).
4. Download the zip. Inside: `app-release-bundle.aab` (upload this), `assetlinks.json`, and the signing key info.
5. Google Play Console (https://play.google.com/console, one-time $25 developer account) → **Create app** → upload the `.aab` under **Testing → Internal testing** first.
6. Play Console → your app → **Setup → App integrity → App signing**: copy the **SHA-256 certificate fingerprint** (Google re-signs the app; use this one, plus the upload-key fingerprint from PWABuilder's assetlinks.json if you want sideloaded builds to work).
7. On the server add to `/srv/kundali/deploy/.env`:
   ```
   TWA_PACKAGE=com.vividbrandify.kundali
   TWA_SHA256=AA:BB:...:FF            # comma-separate several fingerprints
   ```
   then update the server. Check https://kundali.vividbrandify.com/.well-known/assetlinks.json shows your package — without it the app shows a browser bar.
8. Store listing: use `web/icons/screen-phone-1.png`, `screen-phone-2.png` (phone screenshots) and `icon-512.png`; category **Lifestyle**; privacy policy URL can be the home page FAQ until a separate page exists.
9. Promote Internal testing → Production when it looks right.
