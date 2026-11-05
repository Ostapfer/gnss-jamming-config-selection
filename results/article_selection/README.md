# Data-free reconstruction of the article selection example

From the repository root:

```sh
python3 results/article_selection/reproduce_selection.py
```

The script reads the 20 baseline vectors, applies the illustrated functional and resource filters, and checks Pareto sets. It uses only the standard library and does not load raw data or models. The budgets are illustrative and were selected after measurement; this is a descriptive in-sample example, not independent validation. selection_provenance.json identifies the original archived quantities.
