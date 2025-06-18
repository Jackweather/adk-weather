import requests
from bs4 import BeautifulSoup
from transformers import pipeline, AutoTokenizer
import sys
import gc
import time
import os

# Add memory usage reporting
def print_memory_usage(stage=""):
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 ** 2)
        print(f"[MEMORY] {stage} - RSS: {mem_mb:.2f} MB")
    except ImportError:
        pass

# Check system resources before loading model
try:
    import psutil
    available_gb = psutil.virtual_memory().available / (1024 ** 3)
    cpu_count = os.cpu_count()
    if available_gb < 2:
        print(f"[ERROR] Only {available_gb:.2f} GB RAM available. This script requires at least 2GB RAM to run safely.")
        sys.exit(1)
    if cpu_count is not None and cpu_count < 2:
        print(f"[WARNING] Only {cpu_count} CPU detected. Performance may be very slow.")
except ImportError:
    pass

# Optionally, download the model manually with:
#   huggingface-cli download Falconsai/text_summarization_t5_small --local-dir ./local_model_dir
# Then set MODEL_NAME = "./local_model_dir" to avoid repeated downloads and reduce RAM spikes.

MODEL_NAME = "Falconsai/text_summarization_t5_small"
LOCAL_MODEL_DIR = "./local_model_dir"

# Use local model directory if it exists, else fallback to remote
if os.path.isdir(LOCAL_MODEL_DIR):
    model_path = LOCAL_MODEL_DIR
else:
    model_path = MODEL_NAME

# Clean up memory before loading model
gc.collect()
print_memory_usage("Before model load")

# Use a much smaller summarization model to reduce memory usage (<300MB)
summarizer = pipeline(
    "summarization",
    model=model_path,
    tokenizer=model_path,
    device=-1,
    framework="pt",
    fp16=False,
    local_files_only=os.path.isdir(LOCAL_MODEL_DIR)  # Only use local files if available
)
tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=os.path.isdir(LOCAL_MODEL_DIR))

print_memory_usage("After model load")

def fetch_afd(site_code="ALY"):
    """
    Download the Area Forecast Discussion (AFD) from the NWS website for the given site.
    """
    url = (
        f"https://forecast.weather.gov/product.php?"
        f"site={site_code}&issuedby={site_code}&product=AFD&format=CI&version=1&glossary=1&highlight=off"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()  # Stop if there's an error with the request
        soup = BeautifulSoup(response.text, "html.parser")
        afd_element = soup.find("pre")  # Find the forecast text
        if not afd_element:
            raise ValueError("Could not find the forecast text.")
        return afd_element.text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to load the AFD for {site_code}: {e}")
        sys.exit(1)

def chunk_text(text, max_tokens=300):
    """
    Break up the text into smaller chunks so the model can process it.
    """
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        token_length = len(tokenizer.tokenize(word))
        current_chunk.append(word)
        current_length += token_length
        if current_length >= max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def summarize_chunks(chunks, temp_file_path="chunk_summaries.tmp"):
    """
    Summarize each chunk of text separately, write to temp file, and slow memory use.
    """
    with open(temp_file_path, "w") as temp_file:
        for i, chunk in enumerate(chunks):
            print(f"[INFO] Summarizing part {i + 1} of {len(chunks)}...")
            print_memory_usage(f"Before summarizing chunk {i+1}")

            input_tokens = tokenizer(chunk, return_tensors="pt", truncation=True).input_ids.shape[1]
            dynamic_max_length = min(80, int(input_tokens * 0.5))  # Lower max summary length for tiny model

            summary = summarizer(
                chunk,
                max_length=dynamic_max_length,
                min_length=10,
                do_sample=False
            )[0]['summary_text']
            temp_file.write(summary + "\n")
            del chunk, summary
            gc.collect()
            print_memory_usage(f"After summarizing chunk {i+1}")
            time.sleep(0.5)  # Slow down processing to allow memory cleanup

def summarize_afd(site="OKX"):
    """
    Get the AFD and summarize it.
    """
    print(f"[INFO] Getting the forecast discussion for site {site}...")
    afd_text = fetch_afd(site)
    chunks = chunk_text(afd_text, max_tokens=150)  # Smaller chunks for tiny model
    temp_file_path = "chunk_summaries.tmp"
    summarize_chunks(chunks, temp_file_path=temp_file_path)

    del chunks
    gc.collect()

    # Read chunk summaries from temp file
    with open(temp_file_path, "r") as temp_file:
        chunk_summaries = [line.strip() for line in temp_file if line.strip()]

    # Remove temp file
    os.remove(temp_file_path)

    if len(chunk_summaries) == 1:
        result = chunk_summaries[0]
    else:
        print("[INFO] Putting together the final summary...")
        final_summary = summarizer(
            " ".join(chunk_summaries),
            max_length=40,
            min_length=10,
            do_sample=False
        )[0]['summary_text']
        result = final_summary
        del final_summary
        gc.collect()

    del chunk_summaries
    gc.collect()
    return result

if __name__ == "__main__":
    print_memory_usage("Start main")
    site = sys.argv[1].upper() if len(sys.argv) > 1 else "ALY"
    output_file = f"afd_summary_{site}.txt"

    # Clear/truncate the file before generating the summary
    with open(output_file, "w") as f:
        f.truncate(0)

    summary = summarize_afd(site)

    print("\n--- AFD Summary ---\n")
    print(summary)

    with open(output_file, "w") as f:
        f.write(summary)
    print(f"\n[INFO] Saved summary to: {output_file}")

    print_memory_usage("End main")

    # Final memory cleanup
    del summary
    gc.collect()

# Optionally, print a warning if memory is still high
try:
    import psutil
    mem = psutil.virtual_memory()
    if mem.used / (1024 ** 3) > 0.9:
        print("[WARNING] Memory usage is high. Consider further reducing chunk size or using a smaller model.")
except ImportError:
    pass

