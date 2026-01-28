# ❓ Preguntas Frecuentes (FAQs) – ForestGuard

Este documento responde las preguntas más habituales sobre ForestGuard y aborda mitos comunes en torno al uso de datos satelitales, incendios forestales y evidencia ambiental.

---

## 📌 Preguntas Frecuentes

### 1. ¿De dónde provienen los datos de incendios?

ForestGuard utiliza datos oficiales y abiertos de **NASA FIRMS** (sensores **VIIRS y MODIS**) y **Sentinel-2** (ESA / Copernicus). Estas fuentes son estándares internacionales utilizados por gobiernos, universidades y organismos ambientales.

---

### 2. ¿Qué tan confiables son los datos?

Los datos no solo son confiables, sino **auditables y reproducibles**. ForestGuard agrega normalización, trazabilidad y contexto espacial, reduciendo errores de interpretación y falsos positivos.

---

### 3. ¿ForestGuard detecta incendios en tiempo real?

Soporta **ingesta incremental casi en tiempo real**, sujeta a la disponibilidad del feed satelital. Además, mantiene un **histórico completo desde 2015**, ideal para análisis retrospectivo y auditorías.

---

### 4. ¿Cuál es la diferencia entre una detección y un incendio?

Una detección es una anomalía térmica puntual. ForestGuard agrupa múltiples detecciones cercanas en el tiempo y el espacio para identificar **eventos de incendio reales**.

---

### 5. ¿ForestGuard almacena imágenes satelitales?

No. Las imágenes Sentinel-2 se procesan **on-demand** para generar reportes y luego se descartan. Solo se conservan **metadatos y documentos finales**, evitando sobrecargar la infraestructura.

---

### 6. ¿Qué son los certificados ambientales?

Son **documentos PDF verificables**, con hash criptográfico y código QR, que permiten validar públicamente la autenticidad y el contenido del informe generado.

---

### 7. ¿Puede detectar construcciones posteriores a un incendio?

Sí. ForestGuard analiza series temporales de imágenes Sentinel-2 para detectar **cambios en el uso del suelo**, como construcciones, caminos o piletas, incluso años después del incendio.

---

### 8. ¿En qué regiones funciona ForestGuard?

Actualmente el foco es **Argentina**, pero la arquitectura permite escalar fácilmente a otros países que cuenten con datos satelitales equivalentes.

---

### 9. ¿ForestGuard reemplaza a sistemas de alerta temprana?

No. ForestGuard complementa esos sistemas aportando **análisis histórico, auditoría y evidencia**, sin reemplazar brigadas ni alertas operativas.

---

### 10. ¿Quiénes pueden usar ForestGuard?

Está diseñado para organismos públicos, ONGs, empresas, investigadores, periodistas y ciudadanos interesados en auditoría ambiental.

---

## ⚖️ Mitos vs Realidad

### ❌ Mito: “Los datos satelitales no sirven como evidencia”

**✅ Realidad:** Son utilizados globalmente por agencias estatales y organismos internacionales. ForestGuard los convierte en evidencia técnica reproducible mediante trazabilidad y verificación.

---

### ❌ Mito: “Un punto satelital no prueba un incendio”

**✅ Realidad:** Correcto. Por eso ForestGuard no trabaja con puntos aislados, sino con **eventos consolidados** derivados de múltiples detecciones.

---

### ❌ Mito: “Los incendios pequeños no importan”

**✅ Realidad:** Los incendios de baja superficie en zonas sensibles pueden ser indicadores tempranos de degradación ambiental o uso indebido del suelo.

---

### ❌ Mito: “Las imágenes satelitales son imprecisas”

**✅ Realidad:** Sentinel-2 ofrece 10 m de resolución, suficiente para detectar claros, construcciones y cambios significativos en el territorio.

---

### ❌ Mito: “ForestGuard reemplaza brigadas o alertas”

**✅ Realidad:** No las reemplaza; agrega valor aguas abajo con análisis, auditoría y documentación verificable.

---

### ❌ Mito: “Es necesario almacenar todas las imágenes”

**✅ Realidad:** No. ForestGuard procesa imágenes bajo demanda y conserva solo la información esencial.

---

### ❌ Mito: “Los certificados PDF son solo informativos”

**✅ Realidad:** Están diseñados para uso administrativo, legal y de compliance, con hash y QR de verificación.

---

### ❌ Mito: “ForestGuard es un proyecto experimental”

**✅ Realidad:** Cuenta con pipeline operativo, base histórica completa y arquitectura preparada para producción.

---

## 📍 Nota final

ForestGuard busca transformar datos abiertos en **decisiones responsables y evidencia ambiental confiable**, facilitando transparencia y control a largo plazo.
