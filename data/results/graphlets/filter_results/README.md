# Graphlets filtering results

The directory hierarchy explicitly identifies the two graph roles:

```text
query_<color-distribution>_deg_<query-degree>/
└── background_<color-distribution>_deg_<background-degree>/
    └── G_<color-distribution>_deg_<background-degree>_graphlet_cache_filtering_result_<timestamp>.csv
```

There are 12 query configurations and 12 background configurations, giving
144 result CSV files. Each result file contains the outcomes for the 1,000
queries in that query configuration against the indicated background graph.

Absolute paths embedded in the CSV rows are retained as historical provenance
from the original experiment runs; they may therefore contain the older term
`motif`. Numerical result values have not been changed.
