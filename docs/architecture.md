# Zaslón Architecture & Technical Blueprint
**PII Stripper & Data Anonymizer Workbench — Offline B2B Enterprise Edition**

---

## 1. Visión y Justificación Técnica

Las organizaciones B2B que manejan bases de datos sensibles (salud, fintech, retail, auditoría) enfrentan estrictas restricciones regulatorias (GDPR, HIPAA, PCI-DSS, SOC 2, regulaciones locales de protección de datos). Las herramientas tradicionales basadas en la nube exigen subir conjuntos de datos a servidores externos, introduciendo vectores de fuga y riesgos de cumplimiento.

**Zaslón** está diseñado desde sus cimientos como un entorno de escritorio **100% offline y hermético**:
- No ejecuta llamadas de red ni telemetría saliente.
- Opera enteramente sobre el hardware local del cliente.
- Procesamiento modular de alto rendimiento por *chunks* (lotes continuos en memoria), permitiendo anonimizar archivos masivos (cientos de megabytes a varios gigabytes) sin exceder la memoria RAM disponible ni congelar la interfaz de usuario.

---

## 2. Diagrama de Arquitectura Modular

```
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE PRESENTACIÓN                   │
│              PySide6 GUI (Dark Monochromatic QSS)           │
│   ┌────────────────────┐            ┌────────────────────┐  │
│   │ MainWindow         │            │ Telemetry Metrics  │  │
│   │ (Drag & Drop,      │            │ (Rows/sec, Count,  │  │
│   │  Schema Preview)   │            │  Elapsed Timer)    │  │
│   └─────────┬──────────┘            └─────────▲──────────┘  │
│             │                                 │             │
│             │ QThread & Qt Signals            │             │
│   ┌─────────▼─────────────────────────────────┴──────────┐  │
│   │ PipelineWorker (QObject en hilo secundario)          │  │
│   └─────────────────────────┬────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      CAPA DE ORQUESTACIÓN                   │
│          AnonymizationPipeline (Chunk Stream Engine)        │
└──────────────┬──────────────────────┬──────────────────────┬┘
               │                      │                      │
┌──────────────▼─────┐ ┌──────────────▼──────┐ ┌─────────────▼──────┐
│  MOTOR DE INGESTA  │ │  MOTOR DETECCIÓN    │ │ MOTOR TRANSFORM    │
│  (BaseParser)      │ │  (BaseDetector)     │ │ (BaseTransformer)  │
│ ────────────────── │ │ ─────────────────── │ │ ────────────────── │
│ • DataStreamParser │ │ • RegexDetector     │ │ • DataTransformer  │
│   - CSV            │ │   (Luhn Checksum,   │ │   - Masking Token  │
│   - Parquet        │ │    Mod11 Tax IDs,   │ │   - HMAC-SHA256    │
│   - JSON / JSONL   │ │    IPv4/6, Emails,  │ │     Referential    │
│   - Excel (.xlsx)  │ │    Phones)          │ │   - Synthetic Gen  │
│   - Plaintext/Logs │ │ • ONNXNERDetector   │ │   - Suppression    │
│                    │ │   (CPU Standalone)  │ │                    │
└────────────────────┘ └─────────────────────┘ └────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────┐
│                    CAPA DE PERSISTENCIA LOCAL               │
│               SQLite (WAL Mode, Thread-Safe Local)          │
│ • Profiles & Whitelists  • Custom Column Mappings  • Audits │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Principios y Patrones de Diseño Implementados

### 3.1. Inversión de Dependencias (DIP) y Contratos Abstractos
El núcleo no depende de implementaciones concretas de parsers ni de librerías de inferencia. En su lugar, interactúa mediante las clases abstractas definidas en `src/core/interfaces.py`:
- `BaseParser`: Abstrae el streaming secuencial (`read_chunks`) y la escritura incremental (`write_chunk`).
- `BaseDetector`: Define la interfaz unificada de identificación (`detect`, `detect_batch`).
- `BaseTransformer`: Encapsula la lógica de alteración preservando la integridad tipada (`transform_value`).

### 3.2. Gestión de Memoria y Streaming mediante Chunks
Cargar archivos masivos directamente con `pd.read_csv()` o cargando un Parquet completo satura la memoria física. Zaslón utiliza iteradores:
- **CSV:** `pd.read_csv(chunksize=N, low_memory=False)`
- **Parquet:** `pyarrow.parquet.ParquetFile.iter_batches(batch_size=N)`
- **JSON Lines:** `pd.read_json(lines=True, chunksize=N)`
- **Logs:** Generador por streaming de líneas con *buffer* fijo.
La memoria RAM consumida permanece plana e independiente del tamaño del archivo procesado.

### 3.3. Detección Determinista con Validación Algorítmica
Para mitigar falsos positivos habituales en expresiones regulares genéricas:
- **Tarjetas de Crédito:** Se analizan mediante patrones numéricos precompilados y se verifican estrictamente con el **Algoritmo de Luhn** (ISO/IEC 7812). Números de orden, códigos de barras o referencias que no cumplan la suma de comprobación son descartados automáticamente.
- **CUIT/CUIL:** Se verifica el dígito verificador mediante el algoritmo **Módulo 11**.
- **IPv4/IPv6:** Filtrado de rangos reales para evitar falsos positivos con versiones semánticas (ej. `v1.2.3.4`).

### 3.4. Seudonimización con Integridad Referencial
El método `TransformationStrategy.HASH_HMAC` utiliza HMAC-SHA256 con sal (*salt*) criptográfica configurable por perfil. Esto garantiza:
1. **Irreversibilidad:** Imposible reconstruir el PII original sin la clave secreta o sal.
2. **Consistencia Relacional:** El mismo valor (ej. `empresa@cliente.com`) anonimizado en dos tablas distintas produce exactamente el mismo seudónimo determinista (`EMA_9F2A1C80...`), preservando relaciones de clave foránea (*Foreign Keys*) en análisis de datos.

### 3.5. Concurrencia y Reactividad UI (QThread + Worker Pattern)
Para evitar el congelamiento de la ventana de Qt durante cálculos intensivos de CPU:
- Se implementa `PipelineWorker(QObject)` montado en un `QThread` dedicado.
- La comunicación bidireccional ocurre exclusivamente mediante señales y ranuras (*Signals & Slots*) seguras para hilos:
  - `started`: Inicializa estados en UI.
  - `progress(int rows, float speed, int pii_count)`: Actualiza contadores y widgets a 60 fps.
  - `status_message(str)`: Refleja eventos en la barra inferior.
  - `finished(ProcessingMetrics)`: Notifica finalización y persiste en auditoría.
  - `error(str)`: Captura excepciones del hilo y las expone en diálogo modal.
- Soporta cancelación cooperativa limpia (`request_cancellation`).

---

## 4. Estrategia de Empaquetado y Distribución MSIX (Microsoft Store)

Para distribuir en Microsoft Store sin fricciones:
1. **Compilación Binaria con PyInstaller:**
   ```bash
   pyinstaller --noconfirm --onedir --windowed --name "ZaslonWorkbench" --icon "assets/icon.ico" --add-data "assets;assets" --add-data "config;config" main.py
   ```
2. **Generación del Manifiesto de Aplicación (`AppxManifest.xml`):**
   - Configura las capacidades restringidas (restringiendo capacidades de red como `internetClient` para reforzar la naturaleza 100% offline).
3. **Conversión MSIX con MSIX Packaging Tool:**
   - La carpeta `dist/ZaslonWorkbench` se empaqueta en formato `.msix`.
   - Firma digital con certificado de confianza empresarial o firma automática gestionada por Microsoft Partner Center para la Store.
