import os
import json
import time
import logging
from parser import PDFParser1A

# Configure logging for better debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_json_output(parsed_data, pdf_file):
    """
    Validate and clean the JSON output to ensure compliance with expected format.
    """
    if not isinstance(parsed_data, dict):
        logger.warning(f"Invalid data structure for {pdf_file}")
        return {"title": "", "outline": []}
    
    # Ensure title is a string
    title = parsed_data.get('title', '')
    if not isinstance(title, str):
        title = str(title) if title else ''
    
    # Ensure outline is a list with proper structure
    outline = parsed_data.get('outline', [])
    if not isinstance(outline, list):
        outline = []
    
    # Validate each outline item
    validated_outline = []
    for item in outline:
        if isinstance(item, dict) and all(key in item for key in ['level', 'text', 'page']):
            # Ensure proper data types
            validated_item = {
                'level': str(item['level']),
                'text': str(item['text']).strip(),
                'page': int(item['page']) if isinstance(item['page'], (int, float)) else 1
            }
            
            # Filter out empty or invalid entries
            if validated_item['text'] and validated_item['level'] in ['H1', 'H2', 'H3']:
                validated_outline.append(validated_item)
    
    return {
        "title": title.strip(),
        "outline": validated_outline
    }

def process_single_pdf(parser, input_path, output_path, pdf_file):
    """
    Process a single PDF file with comprehensive error handling and validation.
    """
    start_time = time.time()
    
    logger.info(f"Processing {pdf_file}")
    
    try:
        # Parse the PDF
        parsed_data = parser.parse(input_path)
        
        # Validate and clean the output
        validated_data = validate_json_output(parsed_data, pdf_file)
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(validated_data, f, indent=2, ensure_ascii=False)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Successfully processed {pdf_file} in {processing_time:.2f} seconds")
        logger.info(f"Title extracted: '{validated_data['title']}'")
        logger.info(f"Outline items found: {len(validated_data['outline'])}")
        
        return validated_data, processing_time
        
    except Exception as e:
        logger.error(f"Error processing {pdf_file}: {str(e)}")
        # Return minimal valid structure on error
        error_data = {"title": "", "outline": []}
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False)
        
        return error_data, time.time() - start_time

def main():
    """
    Enhanced main processing pipeline with improved error handling and validation.
    """
    # Project structure navigation
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Directory configuration
    input_dir = os.path.join(project_root, 'sample_dataset', 'pdfs')
    output_dir = os.path.join(project_root, 'sample_dataset', 'output')
    model_dir = os.path.join(project_root, 'models')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Validate input directory
    if not os.path.exists(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        return
    
    # Initialize the enhanced parser
    try:
        logger.info("Initializing enhanced PDF parser...")
        parser = PDFParser1A(model_dir=model_dir)
        logger.info("Parser initialization complete.")
    except Exception as e:
        logger.error(f"Failed to initialize parser: {e}")
        return
    
    # Discover PDF files
    pdf_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')])
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    all_parsed_data = []
    total_start_time = time.time()
    
    for pdf_file in pdf_files:
        input_path = os.path.join(input_dir, pdf_file)
        output_filename = os.path.splitext(pdf_file)[0] + '.json'
        output_path = os.path.join(output_dir, output_filename)
        
        # Process individual PDF
        parsed_data, processing_time = process_single_pdf(
            parser, input_path, output_path, pdf_file
        )
        
        all_parsed_data.append(parsed_data)
        
        # Log progress
        logger.info(f"Progress: {len(all_parsed_data)}/{len(pdf_files)} files processed")
    
    # Generate summary output.json (last processed file)
    if all_parsed_data:
        summary_output_path = os.path.join(output_dir, 'output.json')
        with open(summary_output_path, 'w', encoding='utf-8') as f:
            json.dump(all_parsed_data[-1], f, indent=2, ensure_ascii=False)
        logger.info(f"Summary output saved to {summary_output_path}")
    
    # Final processing statistics
    total_time = time.time() - total_start_time
    avg_time = total_time / len(pdf_files) if pdf_files else 0
    
    logger.info("=" * 50)
    logger.info("PROCESSING COMPLETE")
    logger.info(f"Total files processed: {len(pdf_files)}")
    logger.info(f"Total processing time: {total_time:.2f} seconds")
    logger.info(f"Average time per file: {avg_time:.2f} seconds")
    logger.info("=" * 50)

if __name__ == '__main__':
    main()