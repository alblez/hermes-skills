

# Habilidades de Hermes Agent

Una colección de habilidades reutilizables para [Hermes Agent](https://github.com/NousResearch/hermes-agent), el marco de trabajo de agentes de IA de código abierto de Nous Research.

## Habilidades Disponibles

| Habilidad | Descripción |
| --- | --- |
| [qwen3-tts](skills/qwen3-tts/) | Ejecute Qwen3-TTS (texto a voz) localmente en Apple Silicon (MLX) o GPU/CPU (PyTorch). Admite voces personalizadas, diseño de voz y clonación de voz. 10 idiomas, clonación de voz de 3 segundos y control emocional. |
| [upstream-contribution](skills/upstream-contribution/) | Contribuya su proyecto derivado de vuelta al proyecto OSS original sobre el que se construye. Detecta relaciones con el proyecto original, crea un fork del repositorio, agrega su proyecto a su sección de ecosistema/comunidad y abre un PR. También encuentra listas "awesome" relevantes. |

## Instalación

### A través de Hermes Skills Tap (Recomendado)

```bash
# Agregue este repositorio como fuente de habilidades
hermes skills tap add alblez/hermes-skills

# Buscar e instalar
hermes skills search qwen3-tts
hermes skills install alblez/hermes-skills/skills/qwen3-tts
```

### Manual

```bash
# Clone y copie la habilidad que desee
git clone https://github.com/alblez/hermes-skills.git
cp -r hermes-skills/skills/qwen3-tts ~/.hermes/skills/
```

## Estructura

```text
hermes-skills/
├── .gitignore
├── README.md
├── LICENSE
└── skills/
    ├── qwen3-tts/
    │   ├── SKILL.md              # Definición de la habilidad (cargada por Hermes)
    │   ├── requirements.txt      # Dependencias de Python
    │   └── scripts/
    │       └── tts_mlx.py        # Script de inferencia MLX
    └── upstream-contribution/
        ├── SKILL.md              # Definición de la habilidad (cargada por Hermes)
        └── scripts/
            └── scan-upstream-opportunities.py  # Escáner de trabajos programados (cron job)
```

## Contribuir

Cada habilidad reside en su propio directorio bajo `skills/` y debe contener un `SKILL.md` con frontmatter YAML. Consulte la guía de [Creación de Habilidades](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills) para conocer el formato de las habilidades.

## Licencia

Apache-2.0
