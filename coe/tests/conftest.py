import sys
from pathlib import Path
import pytest
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.data.generate_dataset import generate_synthetic_dataset
from src.data.preprocess import preprocess_dataset


@pytest.fixture(scope="session")
def clean_df(tmp_path_factory):
    d = tmp_path_factory.mktemp("d")
    generate_synthetic_dataset(num_records=10500, seed=7, output_path=d / "r.csv")
    return preprocess_dataset(d / "r.csv", d / "p.csv", sample_path=None, verbose=False)


@pytest.fixture(scope="session")
def miner(clean_df):
    from src.models.pattern_miner import MicroStoppageMiner
    return MicroStoppageMiner().fit(clean_df.sample(frac=0.4, random_state=1))
