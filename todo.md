# Chronos geliştirme ve sürüm takip planı

Bu dosya, `AGENTS.md` içindeki bağlayıcı kuralları uygulanabilir sürümlere ve doğrulanabilir iş kalemlerine dönüştüren canlı takip belgesidir. Chronos geliştirilirken ana iş sırası ve sürüm kapıları burada izlenir.

## Takip kuralları

- `[x]` yalnızca iş tamamlandıktan ve kanıtı kaydedildikten sonra kullanılır.
- `[ ]` henüz tamamlanmamış işi gösterir.
- Her sürüm, kendinden önceki sürümün çıkış kapısı geçilmeden başlayamaz.
- Her özellik için geçerli Nox sözdizimi, deterministik test ve derlenen örnek gerekir.
- Bir komut gerçekten çalıştırılmadıysa başarılı kabul edilmez.
- Nox API'si belirsizse önce küçük bir derleme POC'si hazırlanır; API tahmin edilmez.
- `noxc fmt`, `noxc check`, `noxc test`, örnek derlemeleri ve ilgili backend kontrolleri sürüm kanıtına yazılır.
- Ürün kodu ve test aynı sürüm diliminde tamamlanır; belgesiz veya testsiz genel API tamamlanmış sayılmaz.
- Kapsam dışı özellikler, ilgili onay ve doğrulama kapısı açılmadan MVP'ye alınmaz.
- Nox compiler/runtime/stdlib değişikliği ve herhangi bir yayın işlemi açık kullanıcı onayı gerektirir.
- Sürüm numaraları SemVer ile takip edilir. `0.x` içindeki kırıcı değişiklikler de `CHANGELOG.md` ve geçiş notlarında açıkça belirtilir.

## Mevcut durum özeti — 2026-11-09

- [x] Depodaki 976 satırlık `AGENTS.md` baştan sona incelendi.
- [x] Çalışma dizini envanteri çıkarıldı: şu anda yalnızca `AGENTS.md` bulunuyor.
- [x] Dizinin henüz bir Git çalışma ağacı olmadığı doğrulandı.
- [x] Kurulu compiler doğrulandı: `noxc 2.1.0`.
- [x] Kurulu `noxc` komutları ve LLVM/QBE backend seçenekleri incelendi.
- [x] Resmi Nox `time`, `concurrency`, `os`, `fs`, `json`, `test`, paket, modül ve backend belgeleri incelendi.
- [x] Dokümantasyondaki önemli yeni gerçek kaydedildi: `nox.time.boot_ms()` cihaz askıda kaldığında geçen süreyi de kapsayan monoton sayaçtır.
- [x] Dokümantasyondaki önemli yeni gerçek kaydedildi: task cancellation kooperatiftir ve görev bir `await` noktasına ulaşmadıkça çalışmayı kesmez.
- [x] Dokümantasyondaki önemli yeni gerçek kaydedildi: LLVM scheduler çok iş parçacıklı M:N, QBE scheduler tek iş parçacıklı ve kooperatiftir.
- [ ] Belgelerde görülen her kritik API gerçek bir Nox POC'si ile derlenip çalıştırılacak.
- [ ] Kaynak dizin düzeni, paket alias/import davranışı derlenen yerel paket POC'siyle kesinleştirilecek.

## Değişmez ürün sınırları

- Chronos küçük/orta ölçekli, Nox-native, uygulama içi bir zamanlama kütüphanesidir.
- MVP; UTC one-shot, elapsed delay, fixed-rate, fixed-delay, beş alanlı UTC cron, in-memory scheduler, manual tick, senkron executor ve sınırlı execution policy desteğidir.
- Takvim zamanı UTC epoch ile, geçen süre ve beklemeler uygun monoton saatle temsil edilir; bu iki alan birbirine dönüştürülmez.
- Cron MVP'si yalnızca UTC'dir. IANA timezone/DST desteği varmış gibi davranılmaz.
- Trigger hesabı execution'dan ayrıdır; saf trigger kodu uyumaz, task başlatmaz, I/O veya callback çalıştırmaz.
- Varsayılan executor inline/senkron ve varsayılan overlap davranışı `forbid` olur; daha geniş concurrency ancak iki backend'de doğrulanırsa eklenir.
- Gizli global scheduler, import sırasında iş çalıştırma ve kontrolsüz module-level mutable registry kullanılmaz.
- In-memory işlerin process kapanınca kaybolduğu açıkça belgelenir.
- Exactly-once, otomatik timeout enforcement, local-time cron, güvenli task cancellation veya dağıtık koordinasyon doğrulanmadan vaat edilmez.
- Core; Nyx, Aether, Aura, Feather, Nova, Rune veya Noxen'e bağımlı olmaz.
- Shell string, kullanıcı kodu veya cron ifadesi çalıştırılmaz.
- Retry, catch-up, history, event buffer, job sayısı ve concurrency sınırları açık ve sonlu olur.

---

# Phase 0 — `0.0.x` platform doğrulama ve mimari temel

Amaç: Ürün koduna başlamadan önce Nox 2.1.0 gerçeklerini derlenebilir kanıtlarla sabitlemek ve yanlış dizin/API seçimini önlemek.

## 0.0.1 — Depo ve paket iskeleti

- [x] Git kullanım biçimini netleştir ve `main` branch ile yerel depoyu başlat.
- [ ] Phase 0 dosyaları gözden geçirildikten sonra başlangıç commit'ini oluştur.
- [x] Gerçek Nox paket formatına uygun en küçük `nox.json` dosyasını oluştur.
- [x] Harici bağımlılık yoksa `requires` alanını boş tut; gereksiz `nox.lock` üretme.
- [x] Library package için `entry` gereksinimini ve doğru entry dosyasını derleme POC'siyle belirle.
- [x] Tüketici proje POC'si ile dependency alias çözümlemesini doğrula.
- [x] Şu iki yerleşimi deneyip gerçek import yolunu kanıtla:
  - depo kökünde `cron.nox` gibi modüller;
  - `chronos/cron.nox` gibi namespace klasörü.
- [x] Sonuçtan sonra kaynak, test ve örnek dizin düzenini `docs/architecture.md` içine kaydet.
- [x] Yalnızca gerçekten kullanılacak dosya ve dizinleri oluştur; boş placeholder modüller oluşturma.
- [x] Derleme çıktıları, LLVM IR, QBE IL/assembly, test çıktıları ve geçici POC dosyaları için `.gitignore` ekle.
- [x] `README.md`, `CHANGELOG.md` ve `CONTRIBUTING.md` başlangıç içeriklerini oluştur; doğrulanmamış özellik vaat etme.
- [x] Proje lisansını kullanıcı kararıyla MIT olarak seç ve gerçek `LICENSE` dosyasını ekle.

## 0.0.2 — Toolchain ve capability matrisi

- [x] `noxc version` sonucunu, compiler yolunu, host OS/architecture bilgisini ve test tarihini `docs/capabilities.md` içine yaz.
- [x] Kurulu LLVM ve QBE toolchain bileşenlerini doğrula.
- [x] Aynı minimal programı `--backend llvm` ve `--backend qbe` ile derle ve çalıştır.
- [x] `--profile hosted` ve uygun saf modüller için `--profile freestanding` davranışını doğrula.
- [x] `noxc fmt`, `noxc check`, `noxc test`, `noxc build` ve `noxc run` akışlarını küçük proje üzerinde doğrula.
- [x] Her capability için durum, kaynak, compiler sürümü, backend ve `verified / limited / missing` sonucu kaydet.
- [x] Minimum desteklenen Nox sürümünü kanıt olmadan sabitleme; ilk uyumluluk kararını test sonuçlarından sonra ver.

## 0.0.3 — Zaman API'si POC'leri

- [x] `nox.time.now_ms()` duvar saati/UTC epoch davranışını derle ve çalıştır.
- [x] `nox.time.now()` ve `from_epoch_ms()` dönüşümünü doğrula.
- [x] `DateTime` alanlarını ve `to_epoch_ms()` round-trip davranışını sınır örnekleriyle doğrula.
- [x] `DateTime` constructor'ın geçersiz tarihleri kabul edip etmediğini POC ile belirle; Chronos doğrulamasını buna göre tasarla.
- [x] `instant_now()`, `Instant.elapsed_ms()` ve `Duration.as_ms()` kullanımını doğrula.
- [x] `boot_ms()` fark ölçümünü doğrula ve delay semantiğinde suspend süresinin sayılıp sayılmayacağına karar ver.
- [x] `sleep_ms()` çağrısını LLVM ve QBE altında çalıştır; core unit testlerinde gerçek sleep kullanma.
- [x] `sleep_ms()` çağrısının eşzamanlı task'lara etkisini LLVM ve QBE scheduler POC'siyle ölç.
- [x] UTC-only ve timezone API eksikliği bulgusunu `docs/time-semantics.md` ile `docs/timezones.md` içine yaz.
- [x] Epoch, duration ve toplama işlemleri için kullanılacak kesin Nox integer tipini ve overflow davranışını doğrula.

## 0.0.4 — Dil, callback ve hata modeli POC'leri

- [x] Typed function value ile handler geçirme ve çağırmayı doğrula.
- [x] Closure capture ve handler collection içinde saklama davranışını iki backend'de doğrula.
- [x] Class, generic, protocol/arayüz veya seçilecek alternatif dispatch modelini derleyen küçük örneklerle doğrula.
- [x] `T | None`, result alternatifi ve custom exception kullanımını doğrula.
- [x] Handler exception yakalama ve scheduler state'ini koruma için minimal örnek derle.
- [x] Dictionary/list içinde job ve callback saklama sınırlarını doğrula.
- [x] Module-level state'in LLVM worker başına kopyalanması riskini mimari karara dönüştür; core registry'yi module global yapma.
- [x] Reentrant callback'in scheduler'a add/remove çağrısı yapabilmesi için uygun mutation modelini POC ile doğrula.

## 0.0.5 — Concurrency POC'leri ve sınır kararı

- [x] `async def`, `spawn`, `Task[T]`, `await` ve exception propagation örneklerini iki backend'de derle.
- [x] `Task.cancel()` kooperatif cancellation davranışını doğrula; await etmeyen işin kesilemediğini kaydet.
- [x] `Channel[T]` ve kapasite/backpressure davranışını doğrula.
- [x] QBE spawn argüman/sonuç tip kısıtlarını Chronos tasarımı açısından test et.
- [x] `nox.thread`, `ThreadHandle` ve `ThreadChannel` yalnızca background executor için gerçekten gerekliyse incele. MVP manual-tick/inline baseline için gerekli olmadığına karar verildi.
- [x] Güvenli wake-up mekanizması kanıtlanamazsa background scheduler'ı ertele ve manual tick'i resmi portable mod yap.
- [x] Gerçek cancellation/isolation yoksa execution timeout özelliğini desteklenmiyor olarak işaretle.

## 0.0.6 — Mimari karar kayıtları

- [x] Public trigger contract'ını kesinleştir: varsayılan `next_fire_after` strict/exclusive olur.
- [x] Cron grammar kararını kesinleştir: beş alan, UTC, minute resolution, desteklenen wildcard/list/range/step biçimleri.
- [x] DOW numaralandırmasını kesinleştir; Sunday=`0`, MVP'de `7` değerini reddet.
- [x] DOM/DOW kuralını kesinleştir; iki alan restricted ise OR kullan.
- [x] Cron expression uzunluğu, expanded value sayısı, arama yılı ve iteration sınırlarını belirle.
- [x] One-shot geçmiş zaman varsayılanını ve misfire policy ile ilişkisini belirle.
- [x] Fixed-rate anchor ve missed occurrence hesabını belirle.
- [x] Fixed-delay'in completion state'e bağlı olduğunu kaydet; onu saf fixed-rate trigger gibi modelleme.
- [x] Aynı anda due olan işler için deterministik sıralama anahtarını belirle.
- [x] Error taxonomy, timestamp sınırı, duration `0`/negatif/overflow davranışını belirle.
- [x] Temel güvenlik threat modelini `docs/security.md` içine yaz.
- [x] Kararları `docs/architecture.md`, `docs/time-semantics.md`, `docs/cron.md` ve `docs/concurrency.md` içinde kaydet.

### Phase 0 çıkış kapısı

- [x] Kritik hiçbir public API, callback, import, time veya concurrency varsayımı yalnızca dokümana dayanıyor olmasın; gerekli olanlar derlenmiş POC ile kanıtlansın.
- [x] LLVM ve QBE temel POC sonuçları kaydedilmiş olsun.
- [x] `docs/capabilities.md` gerçek komut ve sonuçlarla tamamlanmış olsun.
- [x] Kaynak yerleşimi ve paket import yolu kesinleşmiş olsun.
- [x] MVP destek matrisi ve ertelenen yetenekler açıkça listelenmiş olsun.

---

# Phase 1 — Chronos `0.1.0`: saf zaman, trigger ve UTC cron

Amaç: Scheduler veya gerçek sleep olmadan çalışan deterministik scheduling çekirdeği.

## 0.1.0 — Zaman modeli ve fake clock

- [ ] Doğrulanan Nox tipleriyle UTC epoch timestamp ve nonnegative duration temsilini uygula.
- [ ] Duvar saati ile monoton elapsed time değerlerinin isim ve tür düzeyinde karışmasını engelle.
- [ ] Overflow/underflow kontrollü millisecond arithmetic yardımcılarını uygula.
- [ ] Timestamp destek aralığını ve hata davranışını tanımla.
- [ ] Production clock adapter'ını uygula.
- [ ] Kontrollü advance edilebilen `FakeClock` uygula.
- [ ] Wall-clock forward/backward jump senaryoları için deterministik test ekle.
- [ ] Monotonic delay ve calendar deadline farkını test et.

## 0.1.0 — One-shot ve interval trigger'ları

- [ ] Tek UTC timestamp için one-shot trigger uygula.
- [ ] Exact boundary, past, future ve completed/no-next durumlarını test et.
- [ ] Elapsed delay başlangıç/registration semantiğini uygula ve test et.
- [ ] Fixed-rate trigger'ı initial anchor üzerinden matematiksel hesapla; uzun tekrar döngüsü kullanma.
- [ ] Interval `<= 0`, çok büyük interval ve overflow durumlarını reddet.
- [ ] Missed fixed-rate occurrence hesabının schedule anchor'ı kaydırmadığını test et.
- [ ] Tüm recurring sonuçların strictly increasing olduğunu property benzeri geniş veri setiyle test et.
- [ ] Fixed-delay için yalnızca saf tanım/configuration oluştur; completion tabanlı state transition Phase 2'de scheduler ile tamamlanır.

## 0.1.0 — Beş alanlı UTC cron parser

- [ ] `minute hour day-of-month month day-of-week` alanlarını uygula.
- [ ] `*`, literal, comma list, inclusive range, `*/step` ve `range/step` desteğini uygula.
- [ ] Allowed values koleksiyonlarını sorted/unique hale getir.
- [ ] Yanlış alan sayısı, boş alan, trailing comma, duplicate separator ve invalid token'ları reddet.
- [ ] Step `0`/negatif, reversed range ve out-of-range değerleri reddet.
- [ ] Her parser hatasında alan ve problemli token bilgisini güvenli biçimde döndür.
- [ ] Expression uzunluğu ve expansion sınırlarını uygula.
- [ ] Altı/yedi alanlı ve Quartz `? L W #` ifadelerini açıkça reddet.
- [ ] Parser'ın shell, OS cron, eval veya user code çalıştırmadığını test/inceleme ile doğrula.

## 0.1.0 — Bounded cron next-fire hesabı

- [ ] Strictly-after referanstan bir sonraki minute boundary hesabını uygula.
- [ ] Month/day/hour/minute alanlarında bounded calendar jump yaklaşımı kullan; sınırsız minute scan yapma.
- [ ] Leap year, February 29, month length ve year rollover hesaplarını test et.
- [ ] DOM/DOW OR semantiğinin wildcard/restricted kombinasyonlarını test et.
- [ ] Seconds/milliseconds içeren reference değerlerinde doğru exclusive sonucu test et.
- [ ] Search horizon aşımı ile malformed expression hatasını ayır.
- [ ] Unsatisfiable schedule'ın sonlu sürede `none`/tanımlı hata döndürdüğünü test et.
- [ ] Ardışık next-fire sonuçlarının monoton arttığını golden testlerle doğrula.

## 0.1.0 — Test, örnek ve belge

- [ ] `clock_test.nox`, `trigger_test.nox`, `interval_test.nox`, `cron_test.nox` ve regression testlerini ekle.
- [ ] Saf unit testlerde gerçek sleep ve gerçek sistem saatine bağımlılık bırakma.
- [ ] Derlenen one-shot calculation, fixed-rate calculation ve UTC cron örneklerini ekle.
- [ ] `docs/api.md`, `docs/time-semantics.md` ve `docs/cron.md` içeriklerini gerçek API ile güncelle.
- [ ] `README.md` içine yalnızca 0.1.0'da gerçekten çalışan özellikleri koy.
- [ ] `CHANGELOG.md` içine 0.1.0 değişikliklerini ve bilinen kısıtları yaz.

### `0.1.0` çıkış kapısı

- [ ] Core testlerin tamamı fake clock/deterministik veriyle geçsin; gerçek sleep gerektirmesin.
- [ ] Cron parser ve next-fire araması tüm belirlenmiş resource sınırlarını uygulasın.
- [ ] LLVM ve QBE üzerinde saf testler geçsin.
- [ ] Tüm public 0.1 API'leri belgeli, testli ve en az bir derlenen örnekle kanıtlı olsun.

---

# Phase 2 — Chronos `0.2.0`: manual-tick in-process scheduler

Amaç: Portable, uygulama tarafından sahiplenilen, senkron ve deterministik scheduler.

## Job modeli ve registry

- [ ] Stable job ID, name, trigger, handler, enabled state ve bounded metadata modelini uygula.
- [ ] Duplicate ID için açık error davranışı uygula; implicit replace yapma.
- [ ] Add, inspect/list, enable, disable, remove ve pending cancellation işlemlerini uygula.
- [ ] Running job cancellation ile pending schedule cancellation ayrımını API ve belgede açık tut.
- [ ] Job ID reuse davranışını, aktif run varken ambiguity yaratmayacak şekilde tanımla.
- [ ] Job result/error summary retention sınırını uygula.
- [ ] Executable closure/function pointer serialization yapma.

## Scheduler ve executor

- [ ] `created`, `running`, `stopping`, `stopped`, `failed` lifecycle state'lerini uygula.
- [ ] Start/stop idempotence veya state error davranışını test et.
- [ ] External `now`/clock injection kullanan manual `tick`/`poll` akışını uygula.
- [ ] Scheduling decision ile handler execution katmanlarını ayır.
- [ ] İlk executor olarak inline/synchronous adapter uygula.
- [ ] Kullanıcı handler'ı çalışırken scheduler iç koleksiyon lock/mutation state'ini elde tutma.
- [ ] Callback içinden add/remove yapılmasını safe deferred mutation veya doğrulanmış eşdeğer modelle destekle.
- [ ] Handler exception'ını job failure olarak kaydet; diğer job'ların dispatch'ini bozma.
- [ ] Aynı due timestamp için deterministik dispatch sırası uygula.
- [ ] Scheduler shutdown tamamlandıktan sonra yeni callback başlatılmadığını test et.

## Trigger integration

- [ ] One-shot lifecycle: scheduled, due, completed ve retention davranışını uygula.
- [ ] Fixed-rate recurring işlerin anchor'ını execution süresinden bağımsız koru.
- [ ] Fixed-delay next run'ını gerçek completion timestamp'ından üret.
- [ ] Fixed-delay failure/cancellation sonrası davranışı açıkça tanımla ve test et.
- [ ] UTC cron trigger'ını parser sonucunu tekrar parse etmeden scheduler'a bağla.
- [ ] Exact-boundary ve clock jump senaryolarını fake clock ile test et.

## Temel events ve gözlemlenebilirlik

- [ ] `registered`, `scheduled`, `started`, `succeeded`, `failed`, `cancelled`, scheduler start/stop eventlerini uygula.
- [ ] Event timestamp'lerinde scheduled ve actual değerleri ayır.
- [ ] Duration ölçümünde monoton clock kullan.
- [ ] Listener failure'ın scheduler state'ini bozmasını engelle.
- [ ] Event ve error payload'larında secret/job argument sızıntısı olmamasını incele.

## Test, örnek ve belge

- [ ] Registry, lifecycle, tick, cancellation, ordering, exception recovery ve reentrancy testlerini ekle.
- [ ] Çok sayıda aynı anda due job senaryosunu test et.
- [ ] `once`, `every`, `cron_utc`, `cancel` ve `poll` örneklerini gerçek API ile derle/çalıştır.
- [ ] `docs/scheduler.md`, `docs/jobs.md`, `docs/concurrency.md` ve `docs/api.md` güncelle.
- [ ] README'de manual tick'i portable/default mod olarak göster.
- [ ] In-memory ve process restart'ta job kaybı sınırını görünür biçimde yaz.

### `0.2.0` çıkış kapısı

- [ ] Scheduler unit testlerinin tamamı fake clock ile deterministik geçsin.
- [ ] Handler hatası scheduler koleksiyon/state bütünlüğünü bozmuyor olsun.
- [ ] Hidden thread, global scheduler, unbounded history veya import-time execution bulunmasın.
- [ ] LLVM ve QBE manual scheduler/test/example sonuçları kaydedilmiş olsun.

---

# Phase 3 — Chronos `0.3.0`: bounded execution policies

Amaç: Misfire, overlap, retry ve shutdown davranışlarını açık ve sınırlı hale getirmek.

## Misfire ve coalescing

- [ ] `skip`, `fire_once` ve bounded `catch_up` policy'lerini uygula.
- [ ] Misfire grace period birimini millisecond olarak açıkça tanımla.
- [ ] `max_catch_up_count` ve catch-up time/work budget sınırlarını uygula.
- [ ] Laptop sleep/uzun downtime benzeri büyük ileri saat sıçramasını fake clock ile test et.
- [ ] Coalesced occurrence sayısını bounded metadata/event içinde kaydet.
- [ ] Catch-up'ın cron/fixed-rate anchor'ını değiştirmediğini test et.

## Overlap

- [ ] Default `forbid` davranışını tüm trigger tiplerinde aynı şekilde uygula.
- [ ] `queue_one` için en fazla tek pending occurrence tut.
- [ ] `allow` yalnızca doğrulanmış concurrent executor ve açık `max_concurrent_runs` ile etkinleşsin.
- [ ] Skipped overlap'ın execution count/misfire/history etkisini belge ve test et.
- [ ] Per-job running count/state güncellemelerini race-safe doğrula.
- [ ] Senkron executor'da anlamsız concurrency vaatlerinden kaçın.

## Retry ve failure

- [ ] Default `no retry` davranışını uygula.
- [ ] Bounded fixed-delay retry uygula.
- [ ] Bounded exponential backoff ve maximum delay uygula.
- [ ] Maximum attempt sınırı ve attempt count semantiğini tanımla.
- [ ] Retry ile normal recurrence çakışmasını deterministik policy ile çöz.
- [ ] Handler, scheduler, cancellation ve infrastructure failure kategorilerini ayır.
- [ ] Permanently invalid schedule için retry çalıştırma.
- [ ] Error summary ve execution history retention sınırlarını uygula.
- [ ] Jitter yalnızca injectable deterministic RNG ve açık ihtiyaç varsa eklenir; aksi halde sonraki backlog'a bırakılır.

## Shutdown ve opsiyonel background mode

- [ ] Graceful/immediate stop semantiğini tanımla.
- [ ] Graceful stop beklemesini doğrulanmış ve bounded timeout ile sınırla.
- [ ] Running work ownership'ini kaybetme; tamamlanma/cancellation sınırını açıkça raporla.
- [ ] Safe wake-up ve bounded executor POC'leri iki backend'de başarılıysa background mode uygula.
- [ ] Background mode güvenli değilse bu sürümde manual tick ile kal ve limitation'ı belgede açık bırak.
- [ ] `sleep_ms` ile QBE üzerinde busy-loop veya tüm programı gizlice bloke eden tasarım oluşturma.
- [ ] Execution timeout yalnızca gerçek interruption/isolation kanıtlanırsa sunulsun.

## Test, örnek ve belge

- [ ] Misfire, catch-up cap, overlap, queue-one, retry/backoff/exhaustion ve shutdown testlerini ekle.
- [ ] Policy kombinasyonları için regression matrisi ekle.
- [ ] `retry` örneğini ve destekleniyorsa background lifecycle örneğini derle/çalıştır.
- [ ] `docs/policies.md`, `docs/scheduler.md`, `docs/concurrency.md`, API ve README güncelle.
- [ ] Side-effecting job'lar için idempotency rehberi ekle; exactly-once vaat etme.

### `0.3.0` çıkış kapısı

- [ ] Retry, catch-up, pending overlap, concurrency ve history için sınırsız yol kalmasın.
- [ ] Shutdown testlerinde hidden hang veya shutdown sonrası callback görülmesin.
- [ ] Desteklenmeyen cancellation/timeout/background davranışları dürüstçe işaretlenmiş olsun.

---

# Phase 4 — Chronos `0.4.0`: portability, performans ve API sağlamlaştırma

Amaç: Destek iddialarını gerçek backend/platform kanıtlarıyla eşleştirmek ve MVP API'sini release kalitesine getirmek.

## Backend ve platform matrisi

- [ ] LLVM ve QBE tam test/örnek matrisini çalıştır.
- [ ] QBE single-thread scheduler ve blocking sleep etkisini integration test ile kaydet.
- [ ] macOS için gerçek CI/yerel kanıt oluştur.
- [ ] Linux ve Windows desteğini yalnızca gerçek CI sonucu varsa ilan et.
- [ ] Saf cron/time calculation modüllerinin freestanding derlenebilirliğini test et; başarısızsa limitation yaz.
- [ ] Platform/backend sonuçlarını `docs/compatibility.md` içine tarih ve compiler sürümüyle kaydet.

## Performans ve kaynak sınırları

- [ ] Cron parse ve next-fire benchmark'larını ekle.
- [ ] 100/1k/10k job due lookup benchmark'larını ekle.
- [ ] Scheduler'ın her millisecond tüm job'ları taramadığını incele/ölç.
- [ ] Min-heap veya başka yapı yalnızca ölçüm doğru ihtiyacı gösterirse ve Nox implementasyonu doğrulanırsa kullan.
- [ ] Wake latency, schedule drift ve callback execution süresini ayrı ölç.
- [ ] Memory retention sınırlarını job metadata, event, error ve history için test et.

## API ve entegrasyon

- [ ] Public API yüzeyini küçült ve Stable/Experimental/Internal etiketlerini uygula.
- [ ] Contract testleriyle public API davranışını sabitle.
- [ ] Core bağımlılığı yaratmadan ayrı Nyx/Aether integration örneklerini, ilgili sürümlerle gerçekten derlenebiliyorsa ekle.
- [ ] Breaking 0.x değişikliklerini migration guide ve changelog'a yaz.
- [ ] Security review: parser complexity, secret leakage, callback authority, resource bounds, arbitrary execution.
- [ ] Tüm executable örnekleri CI içinde derle ve çalıştır.

### `0.4.0` çıkış kapısı

- [ ] Uyumluluk tablosundaki her destek iddiasının çalışan CI veya kaydedilmiş test kanıtı olsun.
- [ ] Public MVP API'si testli, belgeli ve gereksiz framework bağımlılıklarından arınmış olsun.
- [ ] Benchmark sonuçları correctness tavizi olmadan kabul edilebilir sınırda olsun.

---

# Phase 5 — Chronos `0.5.x`: opsiyonel persistence — ayrı kullanıcı onayı gerekir

Bu faz MVP'nin parçası değildir. Kullanıcı açıkça onaylamadan implementation başlatılmaz.

- [ ] Store interface'i core scheduler'dan bağımsız tasarla.
- [ ] İlk adapter olarak single-process SQLite kullanımını değerlendir.
- [ ] Nox SQLite API, transactions ve parameterized query davranışını POC ile doğrula.
- [ ] Closure/function pointer yerine handler key ve serializable config persist et.
- [ ] Schema version, migration ve trigger format version alanlarını tasarla.
- [ ] Atomic write, crash aralığı ve restart recovery semantiğini belirle.
- [ ] At-most-once/at-least-once sınırlarını açıkça belge; exactly-once vaat etme.
- [ ] Unknown handler key ve corrupted state senaryolarını test et.
- [ ] Execution history ve error retention sınırlarını uygula.
- [ ] Secret'ları plaintext serialize etme.
- [ ] Crash/restart integration testleri geçmeden durable scheduling iddiasında bulunma.

### `0.5.x` çıkış kapısı

- [ ] Transaction, migration, crash ve recovery davranışları integration testlerle kanıtlanmış olsun.
- [ ] Persistence kullanılmadığında core hâlâ dependency-free/in-memory çalışsın.

---

# Phase 6 — Chronos `0.6+`: ileri scheduling — bağımsız onay ve inceleme gerekir

## IANA timezone ve calendar

- [ ] Lisanslı/sürümlenebilir gerçek IANA tzdata kaynağı doğrulanmadan başlama.
- [ ] Named zone, ambiguous fall-back ve nonexistent spring-forward policy'lerini tasarla.
- [ ] Half-hour/unusual offset, southern hemisphere ve tarihsel transition testleri ekle.
- [ ] Makine locale'ından implicit timezone çıkarma.
- [ ] Tzdata değişiminin persisted schedule davranışını tanımla.

## PostgreSQL ve dağıtık koordinasyon

- [ ] PostgreSQL store'u persistence katmanından ayrı değerlendir.
- [ ] Shared DB'nin tek başına distributed scheduler olmadığı sınırını koru.
- [ ] Lease, fencing token, atomic claim, clock skew ve crash recovery tasarımını bağımsız review'dan geçir.
- [ ] Concurrent claim, duplicate delivery ve network partition testleri olmadan dağıtık destek ilan etme.
- [ ] Delivery semantiğini en az bir kez/en çok bir kez olarak dürüstçe belgele; strict exactly-once kullanma.
- [ ] Redis/Kafka'yı core dependency yapma.

---

# Phase 7 — Chronos `1.0.0`: stabil sürüm

- [ ] Minimal public API'yi Stable olarak dondur.
- [ ] Tüm public API contract testlerini tamamla.
- [ ] README gereksinimlerinin tamamını gerçek ve güncel örneklerle karşıla.
- [ ] Architecture, API, time semantics, cron, scheduler, jobs, policies, concurrency, persistence, timezones, security, compatibility ve roadmap belgelerini tamamla.
- [ ] `CHANGELOG.md` ve `docs/migration-guide.md` içeriklerini release adayıyla eşleştir.
- [ ] Tüm desteklenen OS/backend kombinasyonlarını temiz ortamda tekrar test et.
- [ ] Güvenlik, resource bound, shutdown ve secret leakage incelemesini tamamla.
- [ ] Bilinen tüm limitations listesini yayın notuna koy.
- [ ] Kullanıcı açık onayı olmadan tag, package registry yayını veya release oluşturma.

### `1.0.0` çıkış kapısı

- [ ] İlan edilen tüm davranışlar tekrarlanabilir komutlarla doğrulanmış olsun.
- [ ] Unsupported platform/özellikler açıkça listelensin.
- [ ] SemVer taahhüdü ve migration politikası hazır olsun.
- [ ] Yayın için kullanıcı onayı alınmış olsun.

---

# Ertelenen / kapsam dışı işler

Aşağıdaki maddeler açık bir ürün kararı olmadan aktif fazlara taşınmaz:

- [ ] Distributed workflow engine veya full task queue.
- [ ] İşletim sistemi cron replacement/service installer.
- [ ] REST admin API, dashboard veya network listener.
- [ ] Multi-worker remote execution.
- [ ] Business-day/complex calendar DSL.
- [ ] Shell string veya untrusted code execution.
- [ ] Exactly-once execution iddiası.
- [ ] Otomatik framework bağımlılığı.
- [ ] Sınırsız event/history/retry/catch-up kuyruğu.

---

# Her iş dilimi için zorunlu kontrol listesi

- [ ] Kapsam ve acceptance criteria yazıldı.
- [ ] Mevcut source/test durumu incelendi.
- [ ] Gerekli Nox primitive'i resmi belge, kaynak ve derlenen POC ile doğrulandı.
- [ ] Time semantics ve policy kararı açıklandı.
- [ ] En küçük coherent implementation tamamlandı.
- [ ] Deterministik unit testler eklendi.
- [ ] Gerekliyse sınırlı integration test eklendi.
- [ ] Nox formatter çalıştırıldı.
- [ ] Type-check/build/test/example komutları çalıştırıldı.
- [ ] LLVM/QBE farkı etkileniyorsa iki backend de test edildi.
- [ ] Clock jump, UTC/DST, cancellation, retry, overlap, resource ve secret review yapıldı.
- [ ] API docs, support matrix ve changelog güncellendi.
- [ ] Değişen dosyalar, komutlar, gerçek sonuçlar ve limitations sürüm kanıtına yazıldı.

## Sürüm kanıt şablonu

Her release kapatılırken aşağıdaki bölüm doldurulur:

```text
Sürüm:
Tarih:
Nox compiler:
Host/platform:
Backend'ler:
Değişen dosyalar:
Çalıştırılan komutlar:
Test sonuçları:
Derlenen/çalıştırılan örnekler:
Security/resource review:
Bilinen sınırlamalar:
Çıkış kapısı sonucu:
Kullanıcı onayı gereken sonraki adım:
```

## Resmi doğrulama kaynakları

- Nox deposu: <https://github.com/mburakmmm/nox-lang>
- Nox sitesi: <https://noxlang.com>
- Zaman API'si: <https://github.com/mburakmmm/nox-lang/blob/main/docs/stdlib/time.md>
- Concurrency: <https://github.com/mburakmmm/nox-lang/blob/main/docs/language/concurrency.md>
- Modüller ve paketler: <https://github.com/mburakmmm/nox-lang/blob/main/docs/language/modules.md>
- Paket formatı: <https://github.com/mburakmmm/nox-lang/blob/main/docs/tools/packages.md>
- Test sistemi: <https://github.com/mburakmmm/nox-lang/blob/main/docs/tools/testing.md>
- Backend farkları: <https://github.com/mburakmmm/nox-lang/blob/main/docs/tools/backends.md>

## Sıradaki aktif iş

Phase 1 / `0.1.0`: checked time arithmetic, clock abstraction ve fake clock ile saf zaman modelini uygulamak. Phase 0'dan kalan lisans seçimi ve başlangıç commit'i ayrıca kapatılacak.
