"""Academic Transcript Generator - Higher Success Rate Alternative to Screenshots"""
import random
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


def generate_transcript(first_name: str, last_name: str, school_name: str, dob: str) -> bytes:
    """
    Generate academic transcript (more authentic than screenshots)
    This has higher success rate because:
    - Less pattern recognition risk
    - Looks more like official document
    - Harder for ML to detect as fake
    """
    w, h = 850, 1100
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Try to use system fonts, fallback to default
    try:
        font_header = ImageFont.truetype("arial.ttf", 32)
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_text = ImageFont.truetype("arial.ttf", 16)
        font_bold = ImageFont.truetype("arialbd.ttf", 16)
    except:
        try:
            # Windows fonts
            font_header = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 32)
            font_title = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 24)
            font_text = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
            font_bold = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 16)
        except:
            # Fallback to default
            font_header = font_title = font_text = font_bold = ImageFont.load_default()
    
    # 1. Header
    draw.text((w//2, 50), school_name.upper(), fill=(0, 0, 0), font=font_header, anchor="mm")
    draw.text((w//2, 90), "OFFICIAL ACADEMIC TRANSCRIPT", fill=(50, 50, 50), font=font_title, anchor="mm")
    draw.line([(50, 110), (w-50, 110)], fill=(0, 0, 0), width=2)
    
    # 2. Student Info
    y = 150
    student_id = f"{random.randint(10000000, 99999999)}"
    
    draw.text((50, y), f"Student Name: {first_name} {last_name}", fill=(0, 0, 0), font=font_bold)
    draw.text((w-300, y), f"Student ID: {student_id}", fill=(0, 0, 0), font=font_text)
    y += 30
    draw.text((50, y), f"Date of Birth: {dob}", fill=(0, 0, 0), font=font_text)
    draw.text((w-300, y), f"Date Issued: {datetime.now().strftime('%Y-%m-%d')}", fill=(0, 0, 0), font=font_text)
    y += 40
    
    # 3. Current Enrollment Status (IMPORTANT - shows currently enrolled)
    draw.rectangle([(50, y), (w-50, y+40)], fill=(240, 240, 240))
    
    # Random current semester
    semesters = ["SPRING 2025", "FALL 2024", "SPRING 2026"]
    current_semester = random.choice(semesters)
    
    draw.text((w//2, y+20), f"CURRENT STATUS: ENROLLED ({current_semester})", 
              fill=(0, 100, 0), font=font_bold, anchor="mm")
    y += 70
    
    # 4. Course List with Random Variation
    course_templates = [
        [
            ("CS 101", "Intro to Computer Science", "4.0", "A"),
            ("MATH 201", "Calculus I", "3.0", "A-"),
            ("ENG 102", "Academic Writing", "3.0", "B+"),
            ("PHYS 150", "Physics for Engineers", "4.0", "A"),
            ("HIST 110", "World History", "3.0", "A")
        ],
        [
            ("ECON 101", "Principles of Economics", "3.0", "A"),
            ("PSYCH 100", "Introduction to Psychology", "3.0", "B+"),
            ("BIO 201", "General Biology", "4.0", "A-"),
            ("CHEM 110", "General Chemistry", "4.0", "A"),
            ("MATH 150", "Pre-Calculus", "3.0", "B+")
        ],
        [
            ("CS 201", "Data Structures", "4.0", "A"),
            ("MATH 250", "Linear Algebra", "3.0", "A-"),
            ("ENG 201", "Literature", "3.0", "B"),
            ("STAT 200", "Statistics", "3.0", "A"),
            ("ART 101", "Art History", "3.0", "B+")
        ]
    ]
    
    courses = random.choice(course_templates)
    
    # Table Header
    draw.text((50, y), "Course Code", font=font_bold, fill=(0, 0, 0))
    draw.text((200, y), "Course Title", font=font_bold, fill=(0, 0, 0))
    draw.text((600, y), "Credits", font=font_bold, fill=(0, 0, 0))
    draw.text((700, y), "Grade", font=font_bold, fill=(0, 0, 0))
    y += 20
    draw.line([(50, y), (w-50, y)], fill=(0, 0, 0), width=1)
    y += 20
    
    # Course rows
    for code, title, cred, grade in courses:
        draw.text((50, y), code, font=font_text, fill=(0, 0, 0))
        draw.text((200, y), title, font=font_text, fill=(0, 0, 0))
        draw.text((600, y), cred, font=font_text, fill=(0, 0, 0))
        draw.text((700, y), grade, font=font_text, fill=(0, 0, 0))
        y += 30
    
    y += 20
    draw.line([(50, y), (w-50, y)], fill=(0, 0, 0), width=1)
    y += 30
    
    # 5. Summary
    gpa = round(random.uniform(3.5, 3.95), 2)
    draw.text((50, y), f"Cumulative GPA: {gpa}", font=font_bold, fill=(0, 0, 0))
    draw.text((w-300, y), "Academic Standing: Good", font=font_bold, fill=(0, 0, 0))
    
    # 6. Footer / Watermark
    draw.text((w//2, h-50), 
              "This document is electronically generated and valid without signature.", 
              fill=(100, 100, 100), font=font_text, anchor="mm")
    
    # Save to bytes
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    # Test
    img_data = generate_transcript("John", "Smith", "Test University", "2000-01-15")
    with open("test_transcript.png", "wb") as f:
        f.write(img_data)
    print(f"Generated transcript: {len(img_data)} bytes")
