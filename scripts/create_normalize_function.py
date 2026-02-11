#!/usr/bin/env python3
"""
Create or update a PostgreSQL function for text normalization
that matches Python's .strip().lower() behavior.
"""
import sys
sys.path.insert(0, '.')
from core.database import get_connection_raw, return_connection

# All characters that Python's .strip() removes
WHITESPACE_CODES = [
    0x0009,  # tab
    0x000A,  # newline
    0x000B,  # vertical tab
    0x000C,  # form feed
    0x000D,  # carriage return
    0x001C,  # file separator
    0x001D,  # group separator
    0x001E,  # record separator
    0x001F,  # unit separator
    0x0020,  # space
    0x0085,  # next line
    0x00A0,  # non-breaking space
    0x1680,  # ogham space mark
    0x2000,  # en quad
    0x2001,  # em quad
    0x2002,  # en space
    0x2003,  # em space
    0x2004,  # three-per-em space
    0x2005,  # four-per-em space
    0x2006,  # six-per-em space
    0x2007,  # figure space
    0x2008,  # punctuation space
    0x2009,  # thin space
    0x200A,  # hair space
    0x2028,  # line separator
    0x2029,  # paragraph separator
    0x202F,  # narrow no-break space
    0x205F,  # medium mathematical space
    0x3000,  # ideographic space
]

def main():
    conn = get_connection_raw()
    cur = conn.cursor()
    
    # Build the btrim character string using PostgreSQL CHR()
    chr_list = ' || '.join([f"CHR({code})" for code in WHITESPACE_CODES])
    
    # Create a function that normalizes text like Python's .strip().lower()
    func_sql = f"""
    CREATE OR REPLACE FUNCTION normalize_text_python(text_input TEXT)
    RETURNS TEXT AS $$
    DECLARE
        ws_chars TEXT;
    BEGIN
        -- Build whitespace character string
        ws_chars := {chr_list};
        -- btrim removes leading/trailing chars, LOWER lowercases
        RETURN LOWER(btrim(text_input, ws_chars));
    END;
    $$ LANGUAGE plpgsql IMMUTABLE;
    """
    
    print("Creating function normalize_text_python()...")
    cur.execute(func_sql)
    conn.commit()
    print("Function created!")
    
    # Test the function
    cur.execute("SELECT normalize_text_python(E'  \\n  Hello World  \\xa0\\n  ') as result")
    result = cur.fetchone()['result']
    print(f"Test: normalize_text_python('  \\n  Hello World  \\xa0\\n  ') = '{result}'")
    
    # Compare with Python
    py_result = '  \n  Hello World  \xa0\n  '.strip().lower()
    print(f"Python: '  \\n  Hello World  \\xa0\\n  '.strip().lower() = '{py_result}'")
    print(f"Match: {result == py_result}")
    
    cur.close()
    return_connection(conn)
    
    print("\nNow update work_query to use: normalize_text_python(p.match_text)")

if __name__ == '__main__':
    main()
