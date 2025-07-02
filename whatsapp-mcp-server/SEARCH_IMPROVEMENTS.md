# Mejoras en la Búsqueda de Contactos - WhatsApp MCP

## 🚀 Nuevas Funcionalidades

### 1. Búsqueda Básica Mejorada (`search_contacts`)

**Características principales:**
- ✅ Búsqueda inteligente con múltiples estrategias
- ✅ Scoring avanzado para priorizar resultados relevantes
- ✅ Configuración de límites de resultados
- ✅ Opción para incluir/excluir grupos

**Mejoras implementadas:**
- **Scoring inteligente**: Prioriza coincidencias exactas > inicio de palabra > contiene texto
- **Múltiples patrones**: Busca en nombre y número de teléfono
- **Resultados configurables**: Límite personalizable (default: 25)
- **Filtrado de grupos**: Control de inclusión de grupos (default: solo contactos)

### 2. Búsqueda Inteligente (`smart_search_contacts`)

**Características avanzadas:**
- 🧠 **Algoritmo de similitud Levenshtein**: Maneja errores de escritura
- 🎯 **Threshold configurable**: Control de precisión (default: 0.6)
- 📊 **Scoring múltiple**: Combina similitud de nombre, coincidencias parciales y teléfono
- 🔍 **Fallback automático**: Si no encuentra resultados, usa búsqueda básica

**Casos de uso ideal:**
- Nombres mal escritos o con errores tipográficos
- Búsquedas aproximadas cuando no recuerdas exactamente el nombre
- Contactos con nombres complejos o en otros idiomas

## 📋 Parámetros de las Funciones

### `search_contacts(query, limit=25, include_groups=False)`
- `query`: Término de búsqueda (nombre o teléfono)
- `limit`: Máximo número de resultados (default: 25)
- `include_groups`: Incluir grupos en resultados (default: False)

### `smart_search_contacts(query, limit=25, include_groups=False, similarity_threshold=0.6)`
- `query`: Término de búsqueda (nombre o teléfono)
- `limit`: Máximo número de resultados (default: 25)
- `include_groups`: Incluir grupos en resultados (default: False)
- `similarity_threshold`: Umbral de similitud 0.0-1.0 (default: 0.6)

## 🔧 Algoritmo de Similitud

La función utiliza **distancia de Levenshtein** para calcular similitud entre strings:

```python
def calculate_similarity(s1: str, s2: str) -> float:
    # Retorna valor entre 0.0 (sin similitud) y 1.0 (idéntico)
```

**Ejemplos de similitud:**
- "juan" vs "juan" → 1.0 (idéntico)
- "carlos" vs "karlos" → 0.83 (sustitución c→k)
- "maria" vs "mria" → 0.8 (letra faltante)
- "alejandro" vs "alejandor" → 0.78 (transposición)

## 🎯 Sistema de Scoring

### Búsqueda Básica
- **100 pts**: Coincidencia exacta del nombre
- **90 pts**: Nombre empieza con la búsqueda
- **85 pts**: Número de teléfono empieza con la búsqueda
- **80 pts**: Nombre contiene la búsqueda (límite de palabra)
- **70 pts**: Nombre contiene la búsqueda (cualquier lugar)
- **60 pts**: JID contiene la búsqueda

### Búsqueda Inteligente
- **Similitud de nombre**: Algoritmo Levenshtein
- **Coincidencia parcial**: Búsqueda contenida en palabras
- **Coincidencia telefónica**: Número contiene la búsqueda
- **Score final**: Máximo de los tres scores anteriores

## 📊 Resultados de Pruebas

```
=== PRUEBAS DE SIMILITUD ===
✓ 'juan' vs 'juan': 1.00 (idéntico)
✓ 'maria' vs 'mria': 0.80 (letra faltante)
✓ 'carlos' vs 'karlos': 0.83 (sustitución)

=== PRUEBAS DE BÚSQUEDA ===
Búsqueda: 'juan'
- Básica: 0 resultados
- Inteligente: 1 resultado → Julian (similitud: 0.67)

Búsqueda: 'mar'
- Básica: 2 resultados → Maria Isabel Santa, Augusto Martinez
- Inteligente: 2 resultados → Augusto Martinez, Maria Isabel Santa

Búsqueda: 'carlos'
- Básica: 1 resultado → Carlos Princi
- Inteligente: 2 resultados → Carlos Princi, Cakes (0.50 similitud)
```

## 💡 Recomendaciones de Uso

### Cuándo usar `search_contacts`:
- Búsquedas rápidas con términos conocidos
- Cuando sabes que escribiste correctamente
- Para mejor rendimiento en bases de datos grandes

### Cuándo usar `smart_search_contacts`:
- Nombres complejos o extranjeros
- Cuando no estás seguro de la ortografía
- Búsquedas exploratorias o aproximadas
- Recuperar contactos con nombres similares

## 🔧 Ejecutar Pruebas

```bash
cd whatsapp-mcp-server
python test_search.py
```

## 🚨 Requisitos

- Base de datos WhatsApp Bridge inicializada
- Python 3.7+
- sqlite3

## 📈 Rendimiento

- **Búsqueda básica**: Optimizada para velocidad con índices SQL
- **Búsqueda inteligente**: Mayor procesamiento, mejor precisión
- **Límite recomendado**: 25-50 resultados para óptimo rendimiento
- **Threshold recomendado**: 0.6 para balance precisión/recall

---

*Mejoras implementadas para WhatsApp MCP Server - Julio 2025*
