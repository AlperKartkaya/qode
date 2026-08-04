# Final aşama dış bağımlılık ve açık sorular

Durum tarihi: **2026-08-04**. Aşağıdaki kayıtlar repo içinden doğrulanamayan,
uygulama koduyla çözülemeyen girdilerdir. “Bilinmiyor” değeri mock'a otomatik
geçiş izni vermez.

| Konu | Durum | Owner | Son karar zamanı | Etki / kapanış kanıtı |
| --- | --- | --- | --- | --- |
| Open Gateway `client_id` / `client_secret` | Bilinmiyor | Takım kaptanı + Turkcell koordinasyonu | P5 başlamadan önce | Secret store/env ile gerçek token smoke'u |
| Final SIM ve MSISDN-device binding | Bilinmiyor | Mobil owner + Turkcell koordinasyonu | P6 cihaz provasından önce | Final SIM üzerinde NV başarı/başarısızlık kanıtı |
| Redirect URI, takım VM IP/port allowlist | Bilinmiyor | Backend owner + organizasyon | P5 deploy öncesi | Kayıtlı callback ve dış ağdan health/callback smoke'u |
| Hidden-final timestamp toleransı ve 15 canlı puanın ayrıntısı | Bilinmiyor | Takım kaptanı + organizasyon | P2 evaluator review öncesi | Yazılı resmi cevap veya güncel doküman |
| Lifebox yükleme API/sözleşmesi | Dokümanlarda yok | Mobil owner + organizasyon | P6 öncesi | Resmi API ya da manuel operasyon kararı |
| Android HLS -> MP4 gerçek cihaz spike'ı | Başlamış olduğuna dair repo kanıtı yok | Mobil owner | P6 uygulamasından önce | Tam stream, <=5 dk export, oynatılabilir MP4 ve checksum |
| Harici mobil/backend repo | Repo referansı yok; bu repo seçildi | Teknik lider | ADR-0001 ile kapandı | ADR ve local build/health smoke |
