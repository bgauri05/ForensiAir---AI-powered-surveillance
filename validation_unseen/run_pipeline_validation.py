import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from validation_unseen.run_metrics import run_pipeline_evaluation

if __name__ == "__main__":
    print("==========================================================================")
    print(" FORENSIAIR UNSEEN REAL FACTORY VALIDATION PIPELINE")
    print("==========================================================================")
    run_pipeline_evaluation()
    print("==========================================================================")
    print(" VALIDATION COMPLETE! All metrics CSVs and validation_report.md updated.")
    print("==========================================================================")
