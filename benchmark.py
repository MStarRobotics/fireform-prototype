import json
import time

from fireform.extractor import extract_incident_data as real_extract
from fireform.models import ExtractionResult
from tests.fixtures_incidents import INCIDENTS

def mock_extract(text, schema=None, model="llama3.1", temperature=0.0):

    time.sleep(1.8) # simulate model latency
    
    for inc in INCIDENTS:
        if inc["input"] == text:
            # mock successful return
            return ExtractionResult(data=inc["expected"], attempts=1)
    return ExtractionResult(data={}, attempts=1)

def run_benchmarks(models=["llama3.1", "mistral"], use_mock=False):
    extract_func = mock_extract if use_mock else real_extract
    with open("schemas/incident_schema.json") as f:
        schema = json.load(f)
    print("Model Benchmarking Suite")
    print("=" * 40)
    for model in models:
        print(f"\nModel: {model}")
        success_count = 0
        total_time = 0
        
        for inc in INCIDENTS:
            start = time.time()
            try:
                result = extract_func(text=inc["input"], schema=schema, model=model)
                if result.error:
                    print(f"Error internally: {result.error}")
                    
                data = result.data or {}
                total_time += time.time() - start
                
                match = True
                expected = inc["expected"]
                if data.get("em:IncidentCategoryCode") != expected.get("em:IncidentCategoryCode"):
                    match = False
                
                if match and data:
                    success_count += 1
            except Exception as e:
                print(f"Error for model {model}: {e}")

        if len(INCIDENTS) > 0:
            acc = (success_count / len(INCIDENTS)) * 100
            avg_time = total_time / len(INCIDENTS)
            print(f"Accuracy: {success_count}/{len(INCIDENTS)} ({acc:.1f}%)")
            print(f"Average Time: {avg_time:.2f}s per extraction")

if __name__ == "__main__":
    try:
        import httpx
        r = httpx.get("http://localhost:11434/", timeout=1.0)
        real_ollama = r.status_code == 200
    except Exception:
        real_ollama = False

    if real_ollama:
        print("Real Ollama instance detected! Running actual bench.")
        run_benchmarks(["llama3.1", "mistral", "phi3"], use_mock=False)
    else:
        print("Note: Local Ollama not running. Using deterministic mocking for demo.")
        run_benchmarks(["llama3.1", "mistral", "phi3"], use_mock=True)
