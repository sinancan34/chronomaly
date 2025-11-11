# Chronomaly

**Chronomaly**, Google TimesFM kullanarak zaman serisi tahmini ve anomali tespiti için esnek ve genişletilebilir bir Python kütüphanesidir.

## İçindekiler

- [Problem / Motivasyon](#problem--motivasyon)
- [Özellikler](#özellikler)
- [Kurulum](#kurulum)
- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Kullanım](#kullanım)
  - [Forecast (Tahmin) Workflow](#forecast-tahmin-workflow)
  - [Anomali Tespiti Workflow](#anomali-tespiti-workflow)
  - [Veri Kaynakları](#veri-kaynakları)
- [Mimari](#mimari)
- [Katkıda Bulunma](#katkıda-bulunma)
- [Lisans](#lisans)
- [İletişim / Destek](#i̇letişim--destek)

---

## Problem / Motivasyon

Zaman serisi tahmini ve anomali tespiti, modern veri analitiğinde kritik bir ihtiyaçtır. Ancak:

- **Karmaşıklık**: Güçlü tahmin modelleri (örneğin Google TimesFM) kurmak ve yönetmek teknik olarak zorlayıcıdır
- **Veri Entegrasyonu**: Farklı kaynaklardan (BigQuery, SQLite, CSV, API'ler) veri okumak ve yazmak için tekrarlayan kod gerekir
- **Esneklik Eksikliği**: Çoğu çözüm, veri dönüşümleri, filtreleme ve formatlama için yeterince esnek değildir
- **Anomali Tespiti**: Tahmin edilen değerlerle gerçek değerleri karşılaştırarak anomalileri tespit etmek manuel bir süreçtir

**Chronomaly**, bu sorunları çözmek için tasarlanmıştır:

- Google'ın son teknoloji TimesFM modelini kullanarak güçlü tahminler sağlar
- Çoklu veri kaynakları için hazır reader/writer implementasyonları sunar
- Pipeline tabanlı mimari ile esnek veri dönüşümleri destekler
- Forecast ve actual verileri karşılaştırarak otomatik anomali tespiti yapar
- Modüler yapısı sayesinde kolayca genişletilebilir

---

## Özellikler

- **Google TimesFM Entegrasyonu**: Son teknoloji zaman serisi tahmin modeli desteği
- **Çoklu Veri Kaynakları**:
  - BigQuery, SQLite, CSV okuma/yazma
  - API reader desteği (genişletilebilir)
- **Esnek Workflow Orchestration**:
  - ForecastWorkflow: Veri okuma, dönüştürme, tahmin, yazma
  - AnomalyDetectionWorkflow: Forecast vs actual karşılaştırma
- **Veri Dönüşümleri**:
  - PivotTransformer: Verileri pivot ederek zaman serisi formatına çevirir
  - Filters: Değer filtreleme, cumulative threshold filtreleme
  - Formatters: Yüzde formatlama, sütun formatlama
- **Anomali Tespiti**: Quantile tabanlı anomali tespiti (BELOW_LOWER, IN_RANGE, ABOVE_UPPER)
- **Modüler Mimari**: Her bileşen bağımsız kullanılabilir ve kolayca genişletilebilir
- **Type Safety**: Type hints ile güvenli kod yazımı

---

## Kurulum

### Ön Koşullar

- Python 3.11 veya üzeri
- pip paket yöneticisi

### Temel Kurulum

```bash
# Depoyu klonlayın
git clone https://github.com/insightlytics/chronomaly.git
cd chronomaly

# Temel bağımlılıkları yükleyin
pip install -r requirements.txt

# TimesFM'i GitHub'dan yükleyin (zorunlu)
pip install git+https://github.com/google-research/timesfm.git

# Chronomaly'yi editable mode'da yükleyin
pip install -e .
```

### Opsiyonel Bağımlılıklar

```bash
# BigQuery desteği için
pip install -e ".[bigquery]"

# Geliştirme araçları için (pytest, black, flake8)
pip install -e ".[dev]"

# Tüm opsiyonel bağımlılıklar
pip install -e ".[all]"
```

---

## Hızlı Başlangıç

İşte basit bir tahmin örneği:

```python
import pandas as pd
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.files import CSVDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster

# Veri okuyucu ve yazıcı oluştur
reader = CSVDataReader(
    file_path="data/historical_data.csv",
    date_column="date"
)
writer = CSVDataWriter(file_path="output/forecast.csv")

# Forecaster oluştur
forecaster = TimesFMForecaster(
    model_name='google/timesfm-2.5-200m-pytorch',
    frequency='D'  # Günlük tahmin
)

# Workflow'u çalıştır
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

# 30 günlük tahmin yap
forecast_df = workflow.run(horizon=30)
print(forecast_df.head())
```

---

## Kullanım

### Forecast (Tahmin) Workflow

ForecastWorkflow, veri okuma, dönüştürme, tahmin oluşturma ve yazma işlemlerini orkestre eder.

#### Örnek: CSV'den Okuma ve Pivot Transformation

```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.transformers import PivotTransformer

# CSV okuyucu
reader = CSVDataReader(
    file_path="data/raw_data.csv",
    date_column="date"
)

# SQLite yazıcı
writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts"
)

# Pivot transformer (platformu ve kanalı birleştir)
transformer = PivotTransformer(
    date_column='date',
    columns=['platform', 'channel'],  # Boyutlar
    values='sessions'  # Değer sütunu
)

# Forecaster
forecaster = TimesFMForecaster(frequency='D')

# Workflow
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer,
    transformer=transformer
)

# 7 günlük tahmin
forecast_df = workflow.run(horizon=7)
```

#### Örnek: BigQuery'den Okuma

```python
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

# BigQuery okuyucu
reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    query="""
        SELECT date, metric_name, value
        FROM `project.dataset.table`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """,
    date_column="date"
)

# BigQuery yazıcı
writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    dataset="my_dataset",
    table="forecasts",
    write_disposition="WRITE_APPEND"
)

# Workflow oluştur ve çalıştır
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

forecast_df = workflow.run(horizon=14)
```

### Anomali Tespiti Workflow

AnomalyDetectionWorkflow, tahmin edilen değerlerle gerçek değerleri karşılaştırarak anomalileri tespit eder.

#### Örnek: Temel Anomali Tespiti

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import PivotTransformer

# Forecast verileri okuyucu
forecast_reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-project",
    query="SELECT * FROM `project.dataset.forecasts` WHERE date = CURRENT_DATE()",
    date_column="date"
)

# Actual verileri okuyucu
actual_reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-project",
    query="""
        SELECT date, platform, channel, sessions
        FROM `project.dataset.actuals`
        WHERE date = CURRENT_DATE()
    """,
    date_column="date"
)

# Anomali yazıcı
anomaly_writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-project",
    dataset="analytics",
    table="anomalies"
)

# Actual veriler için pivot transformer
transformer = PivotTransformer(
    date_column='date',
    columns=['platform', 'channel'],
    values='sessions'
)

# Anomali detector
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    date_column='date',
    dimension_names=['platform', 'channel'],  # Metric'i bu boyutlara ayır
    lower_quantile_idx=1,  # q10
    upper_quantile_idx=9   # q90
)

# Workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer
)

# Anomalileri tespit et
anomalies_df = workflow.run()
print(anomalies_df[anomalies_df['status'] != 'IN_RANGE'])
```

#### Örnek: Filtreleme ve Formatlama ile Anomali Tespiti

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.transformers.filters import (
    ValueFilter,
    CumulativeThresholdFilter
)
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

# Transformer pipeline'ı
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer,
    transformers={
        'after_detection': [
            # Sadece anomalileri filtrele
            ValueFilter('status', ['BELOW_LOWER', 'ABOVE_UPPER']),
            # Yüzde formatlama
            ColumnFormatter('deviation_pct', lambda x: f"{x:.1f}%"),
            # Cumulative threshold (opsiyonel)
            CumulativeThresholdFilter(
                value_column='actual',
                threshold=1000,
                group_by=['platform']
            )
        ]
    }
)

anomalies_df = workflow.run()
```

### Veri Kaynakları

Chronomaly, çeşitli veri kaynaklarını destekler:

#### CSV Dosyaları

```python
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.files import CSVDataWriter

reader = CSVDataReader(
    file_path="data/input.csv",
    date_column="date"
)

writer = CSVDataWriter(file_path="output/results.csv")
```

#### SQLite

```python
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

reader = SQLiteDataReader(
    db_path="data/mydb.sqlite",
    table_name="time_series",
    date_column="date"
)

writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts"
)
```

#### BigQuery

```python
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

reader = BigQueryDataReader(
    service_account_file="path/to/credentials.json",
    project="my-gcp-project",
    query="SELECT * FROM `dataset.table` WHERE date > '2024-01-01'",
    date_column="date"
)

writer = BigQueryDataWriter(
    service_account_file="path/to/credentials.json",
    project="my-gcp-project",
    dataset="analytics",
    table="forecasts"
)
```

---

## Mimari

Chronomaly, Clean Architecture prensiplerine göre katmanlı bir yapıya sahiptir:

```
chronomaly/
├── application/          # Uygulama katmanı (workflows)
│   └── workflows/
│       ├── forecast_workflow.py
│       └── anomaly_detection_workflow.py
├── infrastructure/       # Altyapı katmanı (implementasyonlar)
│   ├── forecasters/      # Tahmin modelleri
│   │   ├── base.py
│   │   └── timesfm.py
│   ├── anomaly_detectors/  # Anomali tespit algoritmaları
│   │   ├── base.py
│   │   └── forecast_actual.py
│   ├── transformers/     # Veri dönüşümleri
│   │   ├── pivot.py
│   │   ├── filters/
│   │   └── formatters/
│   ├── data/             # Veri okuma/yazma
│   │   ├── readers/
│   │   │   ├── files/    # CSV vb.
│   │   │   ├── databases/  # SQLite, BigQuery
│   │   │   └── apis/     # API entegrasyonları
│   │   └── writers/
│   │       ├── files/
│   │       └── databases/
│   └── notifiers/        # Bildirim sistemi (genişletilebilir)
└── shared/               # Paylaşılan yardımcılar
```

### Temel Bileşenler

- **Workflows**: İş akışlarını orkestre eder (ForecastWorkflow, AnomalyDetectionWorkflow)
- **Forecasters**: Tahmin modelleri (TimesFMForecaster)
- **AnomalyDetectors**: Anomali tespit algoritmaları (ForecastActualAnomalyDetector)
- **Transformers**: Veri dönüşümleri (PivotTransformer, Filters, Formatters)
- **DataReaders**: Veri okuma (CSV, SQLite, BigQuery)
- **DataWriters**: Veri yazma (CSV, SQLite, BigQuery)

---

## Katkıda Bulunma

Katkılarınızı memnuniyetle karşılıyoruz! İşte nasıl katkıda bulunabileceğiniz:

### Başlangıç

1. Depoyu fork edin
2. Feature branch'i oluşturun: `git checkout -b feature/yeni-ozellik`
3. Değişikliklerinizi commit edin: `git commit -m 'feat: Yeni özellik ekle'`
4. Branch'inizi push edin: `git push origin feature/yeni-ozellik`
5. Pull Request açın

### Kodlama Standartları

- **Type Hints**: Tüm fonksiyonlarda type hints kullanın
- **Docstrings**: Her sınıf ve fonksiyon için docstring ekleyin
- **Testing**: Yeni özellikler için test yazın
- **Code Style**: Black ve flake8 ile kod formatlama

```bash
# Testleri çalıştır
pytest

# Kod formatlama
black chronomaly/

# Linting
flake8 chronomaly/
```

### Commit Mesajları

Conventional Commits formatını kullanın:

- `feat:` Yeni özellik
- `fix:` Bug düzeltmesi
- `docs:` Dokümantasyon
- `refactor:` Kod refactoring
- `test:` Test ekleme/düzeltme
- `chore:` Bakım işleri

### Yeni Veri Kaynağı Ekleme

Yeni bir veri kaynağı eklemek için:

1. `DataReader` veya `DataWriter` base class'ından türetin
2. `load()` veya `write()` metodunu implement edin
3. Test yazın
4. Dokümantasyon ekleyin

Örnek:

```python
from chronomaly.infrastructure.data.readers.base import DataReader
import pandas as pd

class MyCustomReader(DataReader):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def load(self) -> pd.DataFrame:
        # Implementasyonunuz
        pass
```

---

## Lisans

Bu proje [Apache License 2.0](LICENSE) altında lisanslanmıştır.

---

## İletişim / Destek

### Sorun Bildirimi

Bir hata bulduysanız veya öneriniz varsa:

- **GitHub Issues**: [https://github.com/insightlytics/chronomaly/issues](https://github.com/insightlytics/chronomaly/issues)
- Issue açarken lütfen:
  - Sorunu açık bir şekilde tanımlayın
  - Hatayı yeniden üretme adımlarını ekleyin
  - Beklenen ve gerçek davranışı belirtin
  - Python versiyonu ve işletim sistemi bilgisi verin

### Soru ve Tartışma

- **GitHub Discussions**: Genel sorular ve tartışmalar için
- **Pull Requests**: Kod katkıları için

### Dokümantasyon

- **GitHub Repository**: [https://github.com/insightlytics/chronomaly](https://github.com/insightlytics/chronomaly)
- Kod içi docstring'ler ve type hints detaylı kullanım bilgisi sağlar

---

## Yol Haritası

Gelecek sürümlerde planladığımız özellikler:

- [ ] **Ek Forecaster Modelleri**: Prophet, ARIMA, LSTM desteği
- [ ] **Gelişmiş Anomali Tespiti**: ML-based anomaly detection
- [ ] **Visualization**: Tahmin ve anomali görselleştirme araçları
- [ ] **API Server**: REST API ile tahmin servisi
- [ ] **Notifier Entegrasyonları**: Slack, Email, PagerDuty bildirimleri
- [ ] **AutoML**: Otomatik model seçimi ve hiperparametre optimizasyonu
- [ ] **Multi-variate Forecasting**: Çok değişkenli zaman serisi desteği
- [ ] **Real-time Streaming**: Akış verisi üzerinde gerçek zamanlı tahmin

---

**Chronomaly ile güçlü zaman serisi tahminleri ve anomali tespiti yapın!**
