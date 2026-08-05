# Final aşama dış bağımlılık ve açık sorular

Durum tarihi: **2026-08-05**. Aşağıdaki kayıtlar repo içinden doğrulanamayan,
uygulama koduyla çözülemeyen girdilerdir. “Bilinmiyor” değeri mock'a otomatik
geçiş izni vermez.

| Konu | Durum | Owner | Son karar zamanı | Etki / kapanış kanıtı |
| --- | --- | --- | --- | --- |
| Open Gateway `client_id` / `client_secret` | Bilinmiyor | Takım kaptanı + Turkcell koordinasyonu | P5 başlamadan önce | Secret store/env ile gerçek token smoke'u |
| Final SIM ve MSISDN-device binding | Bilinmiyor | Mobil owner + Turkcell koordinasyonu | P6 cihaz provasından önce | Final SIM üzerinde NV başarı/başarısızlık kanıtı |
| Redirect URI, takım VM IP/port allowlist | Bilinmiyor | Backend owner + organizasyon | P5 deploy öncesi | Kayıtlı callback ve dış ağdan health/callback smoke'u |
| OAuth client auth yöntemi, exact authorize/token URL ve scope seti | Yazılı teyit bekliyor | Backend owner + Turkcell koordinasyonu | P5 contract freeze öncesi | Resmi cevap + gerçek token exchange |
| QoD `qosProfile`, `applicationServer`, duration/device kuralları | Dokümanlar arası farklar teyit bekliyor | Backend owner + Turkcell koordinasyonu | P5 contract freeze öncesi | 201 response ve redact edilmiş request contract kanıtı |
| API rate limit, timeout, bakım penceresi ve destek/escalation kanalı | Bilinmiyor | Takım kaptanı + Turkcell koordinasyonu | Canlı prova öncesi | Yazılı operasyon bilgisi |
| Hidden-final timestamp toleransı ve 15 canlı puanın ayrıntısı | Bilinmiyor | Takım kaptanı + organizasyon | P2 evaluator review öncesi | Yazılı resmi cevap veya güncel doküman |
| Lifebox yükleme API/sözleşmesi | Dokümanlarda yok | Mobil owner + organizasyon | P6 öncesi | Resmi API ya da manuel operasyon kararı |
| Android HLS -> MP4 gerçek cihaz spike'ı | Başlamış olduğuna dair repo kanıtı yok | Mobil owner | P6 uygulamasından önce | Tam stream, <=5 dk export, oynatılabilir MP4 ve checksum |
| Harici mobil/backend repo | Repo referansı yok; bu repo seçildi | Teknik lider | ADR-0001 ile kapandı | ADR ve local build/health smoke |

Ayrıntılı talep metni, secret paylaşım kuralları ve uygulama sırası:
[`pending_implementation_info_sheet.md`](pending_implementation_info_sheet.md).
