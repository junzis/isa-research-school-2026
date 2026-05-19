# ISA Research School Lecture

Quarto RevealJS slides for:

**Leveraging Open Data and Models to Reduce Aviation's Climate Footprint**  
ISA Research School, May 2026

## Render

```bash
uv run quarto render lecture.qmd
```

## Live Preview

```bash
uv run quarto preview lecture.qmd --port 8000 --host 0.0.0.0
```

Use another port if `8000` is already occupied.

## Contents

- `lecture.qmd` - main Quarto slide source
- `styles/isa.scss` - RevealJS theme customizations
- `scripts/isa_demo.py` - Python helper functions for runnable examples
- `assets/` - images and small static inputs used by the slides
- `data/` - cached sample data for reproducible rendering
- `lecture.html` and `lecture_files/` - rendered slide deck

## Notes

The deck uses cached sample data so it can render without OpenSky credentials or large weather downloads. Heavy examples, such as full trajectory optimization and live weather interpolation, are shown as code but disabled for rendering.

Generated Quarto caches and the local Python environment are ignored by Git.
