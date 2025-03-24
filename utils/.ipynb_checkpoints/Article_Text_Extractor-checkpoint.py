import re
from typing import Tuple

def extract_title_from_article(article_content: str) -> Tuple[str, str]:
    """
    Extract the title from article content and return both the title and the remaining content.
    
    Args:
        article_content: The full article content
        
    Returns:
        Tuple containing (title, remaining_content)
    """
    # Method 1: Look for the first line that ends with a period or question mark
    lines = article_content.strip().split('\n')
    
    # Remove empty lines
    lines = [line.strip() for line in lines if line.strip()]
    
    if not lines:
        return "No Title Found", article_content
    
    # Try to find a good title candidate in the first few lines
    for i, line in enumerate(lines[:3]):  # Check first 3 non-empty lines
        # If line is reasonably short and ends with punctuation or is all caps, it's likely a title
        if (len(line) < 200 and (line.endswith('.') or line.endswith('?') or line.endswith('!')) or 
            line.isupper() or 
            (len(line.split()) <= 15 and not line.endswith(','))):
            
            # Return the title and the remaining content
            title = line.strip()
            # Remove the title from the content
            remaining_content = '\n'.join(lines[i+1:])
            return title, remaining_content
    
    # Method 2: If no good candidate found, use the first line or a segment of it
    first_line = lines[0].strip()
    
    # If first line is very long, try to find a natural break point
    if len(first_line) > 100:
        # Try to find a natural break (period, question mark, etc.)
        match = re.search(r'[.!?]', first_line[:100])
        if match:
            end_pos = match.start() + 1
            title = first_line[:end_pos].strip()
            remaining_content = first_line[end_pos:].strip() + '\n' + '\n'.join(lines[1:])
            return title, remaining_content
    
    # If all else fails, use the first line or truncate it if it's very long
    if len(first_line) > 150:
        title = first_line[:147] + "..."
    else:
        title = first_line
    
    remaining_content = '\n'.join(lines[1:])
    return title, remaining_content


# Example usage:
if __name__ == "__main__":
    sample_article = """Big Tech Faces New Regulations in EU Market.
    
    The European Union has introduced sweeping new regulations targeting major technology companies operating within its borders. Companies like Google, Amazon, and Facebook will need to comply with stricter data privacy rules and face limitations on how they can use consumer information.
    
    Industry experts predict significant impacts on revenue models and operational practices. "This represents the most significant regulatory challenge these companies have faced in years," said technology analyst Maria Schmidt.
    
    The regulations will take effect in January 2026, giving companies approximately ten months to adapt their systems and policies.
    """
    
    title, content = extract_title_from_article(sample_article)
    print(f"Extracted Title: '{title}'")
    print("\nRemaining Content:")
    print(content)