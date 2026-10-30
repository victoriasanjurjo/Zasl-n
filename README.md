# Zaslón — PII Stripper & Data Anonymizer Workbench

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-green.svg)](https://wiki.qt.io/Qt_for_Python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security: 100% Offline](https://img.shields.io/badge/Security-Air--Gapped%20%2F%20100%25%20Offline-emerald.svg)](#seguridad-y-modo-offline)

**Zaslón** es una estación de trabajo de escritorio orientada al mercado B2B para la **detección, anonimización y seudonimización masiva de datos sensibles (PII)**. Diseñada específicamente para ejecutarse de forma **100% local y aislada de la red (Air-Gapped)**, garantiza el cumplimiento normativo estricto (GDPR, HIPAA, PCI-DSS, SOC 2) sin exponer datos confidenciales a la nube ni a intermediarios externos.

---

## Índice

- [Características Principales](#características-principales)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Árbol de Directorios del Proyecto](#árbol-de-directorios-del-proyecto)
- [Motor de Detección de PII y Reglas Validadas](#motor-de-detección-de-pii-y-reglas-validadas)
- [Estrategias de Transformación de Datos](#estrategias-de-transformación-de-datos)
- [Requisitos y Dependencias](#requisitos-y-dependencias)
- [Guía de Instalación y Ejecución Local](#guía-de-instalación-y-ejecución-local)
- [Ejecución de Pruebas Unitarias](#ejecución-de-pruebas-unitarias)
- [Empaquetado y Distribución MSIX (Microsoft Store)](#empaquetado-y-distribución-msix-microsoft-store)
- [Licencia](#licencia)

---

## Características Principales

1. **100% Local y Libre de Red:** No realiza conexiones salientes, telemetría remota ni envíos de datos.
2. **Streaming por Chunks con Memoria Plana:** Utiliza `pandas` y `pyarrow` para procesar datasets gigantescos por lotes continuos sin saturar la RAM física.
3. **Soporte Multiformato Nativo:**
   - **Tabular:** CSV, Parquet (`.parquet`, `.pq`), Excel (`.xlsx`, `.xls`).
   - **Semi-estructurado:** JSON, JSON Lines (`.jsonl`, `.ndjson`).
   - **Texto no estructurado:** Archivos planos y logs de servidor (`.txt`, `.log`).
4. **Validación Algorítmica de Sumas de Verificación:**
   - Algoritmo de **Luhn** (ISO/IEC 7812) para tarjetas de crédito (eliminando falsos positivos de números de serie o pedidos).
   - Verificación por **Módulo 11** para identificadores tributarios (CUIT/CUIL).
5. **Seudonimización con Integridad Referencial:** Generación de sustitutos mediante **HMAC-SHA256 con sal**, permitiendo unir tablas y conservar relaciones de claves foráneas entre múltiples archivos anonimizados.
6. **Interfaz PySide6 (Qt) con QThread Desacoplado:** Procesamiento en hilos secundarios en tiempo real, con emisión continua de métricas (filas por segundo, entidades identificadas, temporizador) y soporte de arrastrar y soltar (*Drag & Drop*).
7. **Persistencia Local con SQLite:** Almacenamiento seguro en disco local de perfiles de anonimización, listas de exclusión (*whitelists*) y bitácora de auditoría.

---

## Arquitectura del Sistema

El proyecto sigue una arquitectura desacoplada basada en el principio de Inversión de Dependencias (DIP) y separación de responsabilidades:

```
┌────────────────────────────────────────────────────────┐
│                   GUI (PySide6 / Qt)                   │
│   MainWindow ──> Drag&Drop / Schema Preview / Rules    │
│                        │                               │
│           (Qt Signals) │                               │
│                        ▼                               │
│                 PipelineWorker (QThread)               │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│              Orquestador: AnonymizationPipeline        │
│          Ingesta por Chunks ──> Transformación         │
└───────┬────────────────────────┬───────────────────────┘
        │                        │
┌───────▼──────────┐     ┌───────▼──────────┐
│  DataStreamParser│     │  RegexDetector   │
│  (pandas/pyarrow)│     │  (Luhn, Mod11...)│
└──────────────────┘     └───────┬──────────┘
                                 │
                         ┌───────▼──────────┐
                         │  DataTransformer │
                         │  (Mask, HMAC...) │
                         └───────┬──────────┘
                                 │
                         ┌───────▼──────────┐
                         │  DatabaseManager │
                         │  (SQLite Local)  │
                         └──────────────────┘
```

Para una explicación exhaustiva sobre las decisiones de diseño y diagramas detallados, consulte [`docs/architecture.md`](docs/architecture.md).

---

## Árbol de Directorios del Proyecto

```text
Zaslón/
├── assets/                    # Recursos visuales, marcas e íconos de la app
│   ├── icon.ico               # Ícono compilable multirresolución de Windows
│   └── icon.png               # Ícono visual de alta resolución
├── config/                    # Configuraciones de runtime y base de datos local
│   ├── settings.json          # Parámetros y defaults de ejecución
│   └── zaslon_local.db        # Base de datos SQLite (creada al inicio)
├── docs/                      # Documentación técnica y decisiones de diseño
│   └── architecture.md        # Especificación técnica, diagramas y guía MSIX
├── outputs/                   # Directorio de reportes, métricas y datos generados
├── src/                       # Código fuente modular de la aplicación
│   ├── __init__.py
│   ├── core/                  # Contratos, interfaces, tipos y pipeline
│   │   ├── __init__.py
│   │   ├── interfaces.py      # BaseParser, BaseDetector, BaseTransformer (ABCs)
│   │   ├── parsers.py         # Ingesta y exportación streaming (CSV, Parquet, JSON, Logs)
│   │   ├── pipeline.py        # AnonymizationPipeline para procesamiento por chunks
│   │   └── types.py           # Dataclasses, Enums y Métricas de rendimiento
│   ├── db/                    # Persistencia local relacional
│   │   ├── __init__.py
│   │   └── database.py        # SQLite DatabaseManager (perfiles, whitelists, auditoría)
│   ├── engines/               # Motores de análisis y mutación de datos
│   │   ├── __init__.py
│   │   ├── ner_detector.py    # Abstracción desacoplada NER ONNX para CPU
│   │   ├── regex_detector.py  # Regex de alta velocidad con validación de checksums
│   │   └── transformers.py    # Máscaras, HMAC-SHA256 e inyección sintética
│   ├── gui/                   # Interfaz de usuario de escritorio PySide6
│   │   ├── __init__.py
│   │   ├── main_window.py     # Ventana principal, Drag & Drop y visor de esquemas
│   │   ├── styles.py          # Hoja de estilo QSS minimalista y moderna
│   │   └── worker.py          # Worker multihilo desacoplado (QThread)
│   └── models/                # Modelos de datos para capas internas
│       ├── __init__.py
│       └── data_models.py     # ColumnSchema, AnonymizationProfile, AuditRecord
├── tests/                     # Suite de pruebas unitarias y de integración
│   ├── __init__.py
│   └── test_detection_and_pipeline.py # Tests de regex, Luhn, HMAC y pipeline
├── .gitignore                 # Reglas de exclusión de git (.venv, caches, etc.)
├── LICENSE.txt                # Licencia oficial MIT
├── main.py                    # Punto de entrada de la aplicación
├── README.md                  # Este archivo de documentación
└── requirements.txt           # Dependencias exactas del proyecto
```

---

## Motor de Detección de PII y Reglas Validadas

El motor `RegexDetector` cuenta con patrones precompilados y validadores algorítmicos para garantizar una precisión óptima:

| Entidad PII | Tipo de Detección | Validación / Algoritmo | Ejemplo Detectado |
| :--- | :--- | :--- | :--- |
| **Email** | Expresión Regular | RFC 5322 simplificada | `usuario@empresa.com` |
| **Tarjeta de Crédito** | Expresión Regular + Algoritmo | **Algoritmo de Luhn** (ISO/IEC 7812) | `4532-0151-1283-0366` |
| **IPv4 / IPv6** | Expresión Regular | Rangos numéricos de octetos válidos | `192.168.1.100`, `2001:0db8::` |
| **CUIT / CUIL (AR)** | Expresión Regular + Algoritmo | Verificación por **Módulo 11** | `20-28123456-7` |
| **DNI** | Expresión Regular | Rango de 7 a 8 dígitos | `38.291.042` |
| **Teléfonos** | Expresión Regular | Formatos E.164, internacionales y locales | `+1-555-839-2910` |

---

## Estrategias de Transformación de Datos

1. **Direct Masking (`MASK`):** Sustituye la entidad por un token identificador configurable (ej. `[EMAIL_REDACTED]`).
2. **HMAC-SHA256 Seudonimización (`HASH_HMAC`):** Aplica una función de resumen con clave secreta (sal criptográfica). Los mismos valores de entrada reciben el mismo token anónimo dentro del mismo ámbito, posibilitando *joins* SQL sin filtrar información sensible.
3. **Generación Sintética (`SYNTHETIC`):** Crea sustitutos falsos coherentes con el formato esperado (ej. un email de prueba `user_49102@anonymized.internal` o una IP privada clase A `10.x.x.x`).
4. **Supresión (`SUPPRESS`):** Limpia el valor o lo reemplaza por una cadena vacía o nula.

---

## Requisitos y Dependencias

- **Sistema Operativo:** Windows 10/11 (64-bit).
- **Python:** Versión 3.11 o superior.
- **Librerías principales:**
  - `PySide6`: Interfaz gráfica Qt para Python.
  - `pandas` y `pyarrow`: Ingesta, parseo y serialización en memoria por streaming.
  - `openpyxl`: Soporte para hojas de cálculo Excel.
  - `pytest`: Ejecución de pruebas unitarias automatizadas.
  - `PyInstaller`: Compilación de binarios ejecutables para Windows.

---

## Guía de Instalación y Ejecución Local

### 1. Clonar el repositorio y acceder a la carpeta:
```bash
git clone <url-del-repositorio>
cd Zaslón
```

### 2. Crear y activar el entorno virtual (`.venv`):
En PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar las dependencias registradas:
```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación:
```bash
python main.py
```

---

## Ejecución de Pruebas Unitarias

Para correr la suite de pruebas automatizadas:
```bash
pytest tests -v
```

Resultado esperado:
```text
tests/test_detection_and_pipeline.py::test_luhn_validator PASSED
tests/test_detection_and_pipeline.py::test_cuit_validator PASSED
tests/test_detection_and_pipeline.py::test_regex_detector_entities PASSED
tests/test_detection_and_pipeline.py::test_hmac_referential_integrity PASSED
tests/test_detection_and_pipeline.py::test_chunked_pipeline_execution PASSED
tests/test_detection_and_pipeline.py::test_database_persistence PASSED
============================== 6 passed in 1.20s ==============================
```

---

## Empaquetado y Distribución MSIX (Microsoft Store)

### 1. Generar el ejecutable compilado mediante PyInstaller:
```bash
pyinstaller --noconfirm --onedir --windowed --name "ZaslonWorkbench" --icon "assets/icon.ico" --add-data "assets;assets" --add-data "config;config" main.py
```
El binario resultante se encontrará en la carpeta `dist/ZaslonWorkbench/ZaslonWorkbench.exe`.

### 2. Conversión a Paquete MSIX para Microsoft Store:
1. Abra la herramienta oficial **MSIX Packaging Tool** en Windows.
2. Seleccione como instalador o ejecutable el directorio `dist/ZaslonWorkbench`.
3. Configure los datos del paquete con su Publisher ID de Microsoft Partner Center:
   - Nombre: `Zaslon.PIIStripperWorkbench`
   - Editor: `CN=TU_EMPRESA_CERTIFICADA`
4. Declare las capacidades en `AppxManifest.xml` garantizando la ausencia de permisos de red (aislamiento offline).
5. Compile el paquete `.msix` y fírmelo con su certificado o súbalo a Microsoft Store.

---

## Licencia

Distribuido bajo la Licencia **MIT**. Consulte el archivo [`LICENSE.txt`](LICENSE.txt) para más detalles.
