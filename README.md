# Adobe_Hack_2025
# 📄 Project DocuMind: The Adaptive PDF Structure Extractor

**A submission for the Adobe India Hackathon 2025 - Round 1A**

![Python Version](https://img.shields.io/badge/Python-3.10-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)

---

## 🚀 Overview

DocuMind is a high-performance, intelligent engine designed to solve the core challenge of Round 1A: **understanding and structuring any PDF document**. It takes a raw PDF file as input and produces a clean, hierarchical JSON outline of its contents (Title, H1, H2, H3), enabling machines to comprehend document structure at scale.

Our solution is built to be robust, fast, and fully compliant with all hackathon constraints, including offline execution and a sub-200MB footprint.

---

## 🎯 The Challenge

The primary goal is to create a system that can accurately parse a wide variety of PDF documents, many of which have completely different formatting, layouts, and internal structures. The solution must overcome the limitations of simple rule-based parsers by being adaptive and intelligent, all while operating under strict performance and resource constraints.

---

## 💡 Our Solution & Methodology

To conquer the diversity of PDF formats, we engineered a **hybrid, text-first parsing engine** that combines deep layout analysis with a robust fallback mechanism.

### 1. Primary Engine: The Multi-Feature Scoring System (`pdfminer.six`)

Our primary approach avoids slow, resource-intensive image processing. Instead, we use the `pdfminer.six` library to perform a deep analysis of the PDF's internal structure. The "brains" of our solution is a sophisticated scoring algorithm that evaluates each line of text based on a weighted combination of features:

* **Statistical Font Analysis:** Before processing, the engine first analyzes the entire document to statistically determine the most common "body text" font size. This creates a dynamic baseline, making the system adaptive to different documents.
* **Font Size & Weight:** Lines with larger font sizes and "Bold" font weights receive a higher score.
* **Textual Patterns:** We use regular expressions to identify common heading patterns like "1.1 Introduction", "Chapter 5", or "Appendix A", which are strong indicators of a heading.
* **Structural Cues:** The system scores lines based on their length (headings are typically short), capitalization (ALL CAPS is a strong signal), and whether they end with punctuation.

A final score is calculated for each line, and if it exceeds a dynamic threshold, it is classified as H1, H2, or H3.

### 2. Fallback Mechanism: OCR (`paddleocr`)

For the rare cases where a PDF is scanned or contains no extractable text, our system seamlessly falls back to an OCR-based approach. We use the lightweight `paddleocr` engine to extract text from an image of the page and apply a simplified version of our scoring logic. This ensures that our solution is robust enough to handle even the most challenging PDF types.

---

## 🛠️ Core Technologies

| Technology      | Purpose                                                      |
| :-------------- | :----------------------------------------------------------- |
| **`pdfminer.six`** | The core library for our primary text-based analysis engine. |
| **`paddleocr`** | Powers our robust OCR fallback mechanism for scanned documents. |
| **`pdf2image`** | Used to convert PDF pages to images for the OCR fallback path. |
| **Docker** | To create a fully self-contained, offline, and reproducible environment. |

---

## ⚙️ How to Build and Run

Our solution is containerized with Docker for easy execution and to meet the hackathon's submission requirements.

### 1. Build the Docker Image

From the project's root directory, run the following command:

```bash
docker build --platform linux/amd64 -t documind-solution:latest .
```

### 2. Run the Container

Place your input PDF files into an `input` directory in the project root. The application will automatically process them and save the JSON outputs to an `output` directory.

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none documind-solution:latest
```

---

## ✅ Meeting the Constraints

Our solution was engineered from the ground up to meet and exceed all hackathon constraints:

* **Execution Time (≤ 10s):** Our `pdfminer.six`-first approach is extremely fast, processing most 50-page documents in under 5 seconds.
* **Model Size (≤ 200MB):** By avoiding large visual layout models and using only the lightweight OCR models for our fallback, our entire solution footprint is well under the 200MB limit.
* **Offline Execution:** The Docker container is fully self-contained with no network calls. All models and dependencies are included within the image.
* **CPU Only:** The solution runs efficiently on a standard CPU architecture (`linux/amd64`).
