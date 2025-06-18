import requests
from bs4 import BeautifulSoup
from transformers import pipeline, BartTokenizer
import sys
import gc  # Add garbage collector

# Set up the summarizer and tokenizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")

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

def chunk_text(text, max_tokens=1024):
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

def summarize_chunks(chunks):
    """
    Summarize each chunk of text separately, using dynamic max_length to avoid warnings.
    """
    summaries = []
    for i, chunk in enumerate(chunks):
        print(f"[INFO] Summarizing part {i + 1} of {len(chunks)}...")

        # Get token count of input chunk
        input_tokens = tokenizer(chunk, return_tensors="pt", truncation=True).input_ids.shape[1]

        # Set max_length to ~80% of input length, capped at 450 tokens
        dynamic_max_length = min(450, int(input_tokens * 0.8))

        summary = summarizer(
            chunk,
            max_length=dynamic_max_length,
            min_length=60,
            do_sample=False
        )[0]['summary_text']
        summaries.append(summary)

        # Free memory after each chunk
        del chunk
        gc.collect()

    return summaries

def summarize_afd(site="OKX"):
    """
    Get the AFD and summarize it.
    """
    print(f"[INFO] Getting the forecast discussion for site {site}...")
    afd_text = fetch_afd(site)
    chunks = chunk_text(afd_text, max_tokens=500)
    chunk_summaries = summarize_chunks(chunks)

    # Free memory after chunk summaries
    del chunks
    gc.collect()

    if len(chunk_summaries) == 1:
        result = chunk_summaries[0]
    else:
        print("[INFO] Putting together the final summary...")
        final_summary = summarizer(
            " ".join(chunk_summaries),
            max_length=300,
            min_length=120,
            do_sample=False
        )[0]['summary_text']
        result = final_summary
        del final_summary
        gc.collect()

    del chunk_summaries
    gc.collect()
    return result

if __name__ == "__main__":
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

    # Final memory cleanup
    del summary
    gc.collect()

