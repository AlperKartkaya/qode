# QoDe Road Safety — Native Android Application (Kotlin)

Native Android application built with Kotlin, Jetpack Compose, Media3 ExoPlayer, and Retrofit.

## 📱 Features

1. **Number Verification (NV)**:
   - Backend-owned OIDC flow starts at `GET /api/auth/start?mobile=true`.
   - The backend returns to `qode://auth/callback`; Android then calls `POST /api/number-verification/verify` with the opaque flow ID.
   - HTTP/network failures block entry. There is no local/mock success fallback.
   - Live Connection logs console for debugging.

2. **Quality on Demand (QoD)**:
   - Network quality request through `POST /api/qod/sessions` with the verified flow ID.
   - Dynamic profile badge (`1080p Boosted` vs `240p Standard`).

3. **HLS Video Streaming & Direct MP4 Recording**:
   - Built-in Media3 ExoPlayer for adaptively playing TEKNOFEST HLS video stream.
   - **Native HLS Downloader**: Programmatically fetches HLS playlist segments, downloads, and concatenates them directly into a local `.mp4` file with real-time progress bar.

4. **ZIP & Lifebox Sharing**:
   - Compresses the recorded `.mp4` stream into a `.zip` archive.
   - Invokes Android system share sheet (`FileProvider` + `Intent.ACTION_SEND`) to share directly via Lifebox or email to contest judges.

5. **Backend Video Upload & AI Inference**:
   - Multipart file upload of recorded `.mp4` to backend (`POST /upload`).
   - Triggers AI inference container (`POST /ai-run`).

6. **Inference Results Viewer**:
   - Real-time polling (`GET /ai-result`).
   - Displays vehicle identification (type, plate, color, confidence score).
   - Displays timeline detection events with category, label, and timestamp.
   - Formatted raw JSON viewer.

## 🚀 Building & Running

### Requirements
- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34 (Android 14)
- JDK 17

### Commands
Open the project in Android Studio or build via Gradle:
```bash
QODE_API_BASE_URL="http://<BACKEND_HOST>:8000/" ./gradlew testDebugUnitTest assembleDebug
```

`QODE_API_BASE_URL` is compiled into the APK. Resolution order is Gradle property,
environment variable, then the API base derived from `OPENGW_REDIRECT_URI` or
`BACKEND_CALLBACK_URL` in the ignored root `.env`. Only a debug build without any
of these settings falls back to emulator-only `http://10.0.2.2:8000/`; release
builds fail instead. Rebuild and reinstall the APK whenever the target changes.
