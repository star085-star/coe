"""One command: generate -> clean -> train/evaluate -> reports.   python run_pipeline.py [--multi-seed]"""
import subprocess, sys
from src.data.generate_dataset import generate_synthetic_dataset
from src.data.preprocess import preprocess_dataset
from src.evaluation.evaluate import run

if __name__ == "__main__":
    generate_synthetic_dataset(); preprocess_dataset()
    if "--multi-seed" in sys.argv:
        subprocess.run([sys.executable, "scripts/multi_seed.py"], check=True)
    r = run()
    for t in r["targets"]:
        print("PASS" if t["pass"] else "FAIL", t["metric"], t["measured"])
