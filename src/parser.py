import os
import json
import numpy as np
import re
from PIL import Image
import cv2
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LAParams, LTTextBox, LTTextLine
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from collections import Counter, defaultdict

class PDFParser1A:
    def __init__(self, model_dir='models'):
        """
        Enhanced PDF parser with sophisticated heading detection algorithms.
        """
        print("Initializing Enhanced PaddleOCR...")
        self.ocr = PaddleOCR(
            use_angle_cls=True, 
            lang='en', 
            use_gpu=False,
            ocr_version="PP-OCRv3",
            rec_model_dir=os.path.join(model_dir, 'en_PP-OCRv3_rec_infer'),
            cls_model_dir=os.path.join(model_dir, 'ch_ppocr_mobile_v2.0_cls_infer'),
            det_model_dir=os.path.join(model_dir, 'en_PP-OCRv3_det_infer')
        )
        
        # Heading pattern recognition
        self.heading_patterns = [
            r'^[A-Z][A-Z\s&-]+$',  # All caps headings
            r'^\d+\.\s+[A-Z]',      # Numbered sections
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*:?$',  # Title case
            r'^[IVX]+\.\s+',        # Roman numerals
            r'^Chapter\s+\d+',      # Chapter headings
            r'^Section\s+\d+',      # Section headings
        ]
        
        # Common non-heading patterns to exclude
        self.exclusion_patterns = [
            r'^\d+$',  # Pure numbers
            r'^page\s+\d+$',  # Page numbers
            r'^www\.',  # URLs
            r'@',  # Email addresses
            r'^\([^)]+\)$',  # Parenthetical text
        ]
        
        print("Enhanced PaddleOCR initialized with advanced pattern recognition.")
    
    def _extract_font_statistics(self, pages):
        """
        Advanced font analysis with statistical distribution modeling.
        """
        font_data = defaultdict(lambda: {'count': 0, 'positions': [], 'contexts': []})
        
        for page_num, page in enumerate(pages):
            for element in page:
                if isinstance(element, LTTextContainer):
                    text = element.get_text().strip()
                    if not text:
                        continue
                        
                    # Extract character-level font information
                    char_fonts = []
                    for line in element:
                        if hasattr(line, '__iter__'):
                            for char in line:
                                if isinstance(char, LTChar):
                                    char_fonts.append({
                                        'size': round(char.size, 1),
                                        'fontname': getattr(char, 'fontname', 'unknown'),
                                        'bold': 'bold' in getattr(char, 'fontname', '').lower(),
                                        'y_pos': char.y0
                                    })
                    
                    if char_fonts:
                        # Determine dominant font characteristics
                        sizes = [cf['size'] for cf in char_fonts]
                        dominant_size = Counter(sizes).most_common(1)[0][0]
                        
                        # Use the same key as used in char_fonts (rounded size)
                        font_data[dominant_size]['count'] += len(text.split())
                        font_data[dominant_size]['positions'].append(page_num)
                        font_data[dominant_size]['contexts'].append(text[:50])
        
        return dict(font_data)
    
    def _classify_heading_levels(self, font_stats):
        """
        Sophisticated heading classification using statistical analysis.
        """
        if not font_stats:
            return {}
        
        # Sort fonts by size (descending)
        sorted_fonts = sorted(font_stats.items(), key=lambda x: x[0], reverse=True)
        
        # Identify body text (most frequent font size)
        body_font_candidate = max(font_stats.items(), key=lambda x: x[1]['count'])
        body_font_size = body_font_candidate[0]
        
        # Classify heading levels based on size differential and usage patterns
        heading_map = {}
        level_counter = 1
        
        for font_size, stats in sorted_fonts:
            # Skip if too similar to body text or used too frequently
            size_ratio = font_size / body_font_size
            
            if size_ratio > 1.15 and stats['count'] < body_font_candidate[1]['count'] * 0.3:
                if level_counter == 1:
                    heading_map[font_size] = 'H1'
                elif level_counter == 2:
                    heading_map[font_size] = 'H2'
                elif level_counter == 3:
                    heading_map[font_size] = 'H3'
                else:
                    break
                level_counter += 1
        
        return heading_map, body_font_size
    
    def _is_potential_heading(self, text, font_size=None, body_size=None):
        """
        Advanced heading detection using multiple heuristics.
        """
        if not text or len(text.strip()) < 2:
            return False
        
        text = text.strip()
        
        # Exclude common non-headings
        for pattern in self.exclusion_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        # Length-based filtering
        if len(text) > 200 or len(text.split()) > 20:
            return False
        
        # Pattern matching for common heading structures
        for pattern in self.heading_patterns:
            if re.match(pattern, text):
                return True
        
        # Font-based classification (if available)
        if font_size and body_size:
            if font_size > body_size * 1.1:
                return True
        
        # Structural indicators
        if text.endswith(':') and len(text.split()) <= 5:
            return True
        
        # Position-based heuristics (typically headings are shorter)
        if len(text.split()) <= 8 and text[0].isupper():
            return True
        
        return False
    
    def _extract_title_candidates(self, first_page_elements):
        """
        Enhanced title extraction with multiple candidate evaluation.
        """
        candidates = []
        
        for element in first_page_elements:
            text = element.get_text().strip()
            if not text:
                continue
            
            # Extract font information
            font_sizes = []
            for line in element:
                if hasattr(line, '__iter__'):
                    for char in line:
                        if isinstance(char, LTChar):
                            font_sizes.append(char.size)
            
            if font_sizes:
                avg_font_size = np.mean(font_sizes)
                candidates.append({
                    'text': text,
                    'font_size': avg_font_size,
                    'y_position': element.y0,
                    'word_count': len(text.split()),
                    'char_count': len(text)
                })
        
        if not candidates:
            return ""
        
        # Score candidates based on multiple factors
        for candidate in candidates:
            score = 0
            
            # Font size weight (larger = better for title)
            max_font = max(c['font_size'] for c in candidates)
            score += (candidate['font_size'] / max_font) * 40
            
            # Position weight (higher on page = better)
            max_y = max(c['y_position'] for c in candidates)
            score += (candidate['y_position'] / max_y) * 30
            
            # Length optimization (not too short, not too long)
            ideal_length = 6  # words
            length_score = max(0, 20 - abs(candidate['word_count'] - ideal_length) * 2)
            score += length_score
            
            # Avoid very long candidates
            if candidate['word_count'] > 15:
                score -= 20
            
            candidate['score'] = score
        
        # Return highest scoring candidate
        best_candidate = max(candidates, key=lambda x: x['score'])
        return best_candidate['text']
    
    def _parse_with_pdfminer(self, pdf_path):
        """
        Enhanced PDFMiner parsing with sophisticated text analysis.
        """
        print(f"Enhanced parsing with pdfminer: {pdf_path}")
        try:
            pages = list(extract_pages(pdf_path, laparams=LAParams()))
            if not pages:
                return None
            
            # Extract font statistics across all pages
            font_stats = self._extract_font_statistics(pages)
            heading_map, body_font_size = self._classify_heading_levels(font_stats)
            
            # Extract title from first page
            first_page_elements = [el for el in pages[0] if isinstance(el, LTTextContainer)]
            title = self._extract_title_candidates(first_page_elements)
            
            # Extract outline
            outline = []
            seen_headings = set()  # Avoid duplicates
            
            for page_num, page in enumerate(pages):
                for element in page:
                    if isinstance(element, LTTextContainer):
                        text = element.get_text().strip()
                        if not text or text in seen_headings:
                            continue
                        
                        # Extract font characteristics
                        font_sizes = []
                        for line in element:
                            if hasattr(line, '__iter__'):
                                for char in line:
                                    if isinstance(char, LTChar):
                                        font_sizes.append(char.size)
                        
                        if font_sizes:
                            dominant_size = Counter([round(s, 1) for s in font_sizes]).most_common(1)[0][0]
                            
                            # Check if it's a heading based on font mapping
                            heading_level = heading_map.get(dominant_size)
                            
                            # Alternative heading detection if font mapping fails
                            if not heading_level and self._is_potential_heading(text, dominant_size, body_font_size):
                                # Assign level based on font size relative to body
                                size_ratio = dominant_size / body_font_size if body_font_size > 0 else 1
                                if size_ratio > 1.5:
                                    heading_level = 'H1'
                                elif size_ratio > 1.25:
                                    heading_level = 'H2'
                                elif size_ratio > 1.1:
                                    heading_level = 'H3'
                            
                            if heading_level and text != title:
                                outline.append({
                                    "level": heading_level,
                                    "text": text,
                                    "page": page_num + 1
                                })
                                seen_headings.add(text)
            
            return {"title": title, "outline": outline}
            
        except Exception as e:
            print(f"Enhanced pdfminer failed: {e}")
            return None
    
    def _parse_with_ocr(self, pdf_path):
        """
        Enhanced OCR parsing with structural analysis.
        """
        print(f"Enhanced OCR parsing for: {pdf_path}")
        try:
            images = convert_from_path(pdf_path)
            title = ""
            outline = []
            seen_headings = set()
            
            for page_num, img in enumerate(images):
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                result = self.ocr.ocr(img_cv, cls=True)
                
                if result and result[0]:
                    # Analyze text blocks for structural patterns
                    text_blocks = []
                    for block in result[0]:
                        bbox, (text, confidence) = block
                        if confidence > 0.7:  # Quality threshold
                            # Calculate position and size metrics
                            x_coords = [point[0] for point in bbox]
                            y_coords = [point[1] for point in bbox]
                            
                            text_blocks.append({
                                'text': text.strip(),
                                'confidence': confidence,
                                'x_center': np.mean(x_coords),
                                'y_center': np.mean(y_coords),
                                'width': max(x_coords) - min(x_coords),
                                'height': max(y_coords) - min(y_coords),
                                'area': (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))
                            })
                    
                    # Sort by vertical position (top to bottom)
                    text_blocks.sort(key=lambda x: -x['y_center'])  # Negative for top-first
                    
                    # Extract title from first page
                    if page_num == 0 and not title and text_blocks:
                        # Find potential title (usually largest text near top)
                        title_candidates = text_blocks[:3]  # Top 3 blocks
                        if title_candidates:
                            best_title = max(title_candidates, key=lambda x: x['area'])
                            title = best_title['text']
                    
                    # Extract headings
                    for block in text_blocks:
                        text = block['text']
                        
                        if (text and text not in seen_headings and 
                            text != title and 
                            self._is_potential_heading(text)):
                            
                            # Simple heuristic for heading levels based on text characteristics
                            if re.match(r'^[A-Z][A-Z\s]+$', text) or text.isupper():
                                level = 'H1'
                            elif re.match(r'^\d+\.', text) or text.endswith(':'):
                                level = 'H2'  
                            else:
                                level = 'H3'
                            
                            outline.append({
                                "level": level,
                                "text": text,
                                "page": page_num + 1
                            })
                            seen_headings.add(text)
            
            return {"title": title, "outline": outline}
            
        except Exception as e:
            print(f"Enhanced OCR failed for {pdf_path}: {e}")
            return None
    
    def parse(self, pdf_path):
        """
        Main parsing orchestrator with fallback mechanisms.
        """
        # Try PDFMiner first (better for text-based PDFs)
        result = self._parse_with_pdfminer(pdf_path)
        
        # Fallback to OCR if PDFMiner fails or produces poor results
        if not result or (not result.get('title') and not result.get('outline')):
            ocr_result = self._parse_with_ocr(pdf_path)
            if ocr_result:
                # Merge results if both have partial success
                if result:
                    merged_result = {
                        'title': result.get('title') or ocr_result.get('title', ''),
                        'outline': result.get('outline', []) + ocr_result.get('outline', [])
                    }
                    # Remove duplicates
                    seen = set()
                    unique_outline = []
                    for item in merged_result['outline']:
                        if item['text'] not in seen:
                            unique_outline.append(item)
                            seen.add(item['text'])
                    merged_result['outline'] = unique_outline
                    return merged_result
                else:
                    result = ocr_result
        
        # Final fallback
        if not result:
            return {
                "title": os.path.basename(pdf_path).replace('.pdf', ''),
                "outline": []
            }
        
        return result