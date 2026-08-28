Analysis code

The two notebooks are the best place to start. The first introduces the
prepared data, and the second contains the calculations reported in the
manuscript. Both are saved with their outputs.

CONTENTS

01_data_overview.ipynb provides focused exploratory data analysis of the
supplied tables. It shows sample sizes, assessment frequencies, disease
categories, and two simple diagnostic plots. The notebook is saved with
executed cells so that its tables and plots can be reviewed immediately.

02_manuscript_analyses.ipynb contains the calculations for repeated candidate
identification and the exact distribution of disease overlap. Its code cells show
each calculation directly and write four tables containing the calculated results.
This notebook is also saved with executed cells.

The remaining Python files have distinct roles:

  run_all.py                       Executes both notebooks and checks the results.
  validate_release.py              Checks recalculated results and repository files.
  build_recurrent_registry.py      Rebuilds the table of 171 repeatedly identified candidates.
  generate_figures.py              Rebuilds Figures 1 to 3 and Figure S1.
  build_supplementary_workbook.py  Rebuilds the supplementary workbook.

RUN THE ANALYSES

1. Create a Python 3.11 environment.
2. Install the recorded package versions:

   python -m pip install -r requirements.txt

3. From this directory, run:

   python run_all.py --package-root /path/to/package --output-dir /path/to/results

The results directory will contain executed copies of both notebooks, four
analysis tables, a reconstructed copy of the candidate registry, and
analysis_validation.json. A successful run reports that all values agree.

The notebooks use paths relative to this package when opened from this
directory. `run_all.py` supplies the package and result locations automatically.

SCIENTIFIC CALCULATIONS

Repeated candidate identification

The first analysis uses 10,000 permutations and random-number seed 20260714.
Within each independent screen, every permutation keeps
the assessed accessions or lines and the observed candidate count fixed, then
samples that number of candidates without replacement. The calculation records
the proportion identified in at least two independent screens among candidates
identified at least once and assessed in at least two independent screens. The
two-sided empirical probability uses a plus-one correction in each tail and
doubles the smaller tail.

Direct disease comparisons

For a two-disease comparison, the overlap follows the exact hypergeometric
distribution after conditioning on the number assessed and the number classified
favorably for each disease. For a three-disease comparison, the calculation sums
over the overlap of the first two diseases and then over the intersection of the
third disease with accessions or lines classified favorably for exactly one of the first two.
Discrete convolution combines the five comparison distributions. The reported
interval contains the 0.025 and 0.975 cumulative quantiles.

OTHER REPRODUCIBLE MATERIALS

To rebuild the detailed and supplementary candidate registries:

   python build_recurrent_registry.py \
       --memberships ../data/analysis_inputs/Recurrent_Candidate_Qualifying_Memberships.csv \
       --citations ../../supplement/Recurrent_Candidate_Source_Citations.csv \
       --output /path/to/Recurrent_Candidate_Registry_detailed.csv \
       --reader-output /path/to/Recurrent_Candidate_Registry.csv

To regenerate the manuscript figures from the supplied figure data:

   python generate_figures.py \
       --data-dir ../data/figure_source_data \
       --output-dir /path/to/regenerated_figures

Figure generation uses installed Arial regular and bold faces. Plot text is
Arial 9 pt, and panel letters are Arial 14 pt bold, matching the manuscript.

To rebuild the supplementary workbook:

   python build_supplementary_workbook.py \
       --tables-dir ../data/supplementary_tables \
       --output /path/to/Supplementary_Tables_S1-S17.xlsx

DATA PROVIDED FOR REPRODUCTION

The anonymized table for repeated candidate identification records each
anonymous accession or line in every independent screen where it was assessed
and whether it met the study criterion.
The table for direct comparisons supplies the number assessed, the number
classified favorably for each disease, and the observed number classified
favorably for multiple diseases.
The table of qualifying results supplies 401 observations in which a candidate
met a study criterion. These observations represent 349 unique combinations of
the 171 candidates and independent screens.

These tables reproduce the reported aggregate analyses while observing the
source publications' terms for sharing phenotype measurements. Original
measurements can be obtained from the cited publications, repositories, or
rights holders under their applicable terms.
