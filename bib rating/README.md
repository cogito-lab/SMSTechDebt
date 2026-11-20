# BibTeX Screening and Rating

This folder contains supporting materials used for BibTeX-based paper screening and rating in the systematic mapping study on Technical Debt.

## Folder Structure

### `scripts/`
- `rate_bibtex_ollama.py` — Rates BibTeX entries using a locally running Ollama model.
- `quick_dry_run_ollama.py` — Performs a small test run of the rating process.
- `five_star_links.py` — Extracts links associated with five-star-rated entries.

### `prompts/`
- `prompt final revised.xml` — Contains the prompt used for LLM-based paper rating.

### `data/`
- `five_star_links.csv` — Contains links extracted for five-star-rated papers.

## Notes

These materials document the LLM-assisted BibTeX screening workflow.

The scripts may require adjustments to input and output file paths, local dependencies, and Ollama model configuration before execution.

The original research-paper PDFs and local Python virtual environments are not included in this repository.